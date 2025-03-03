from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc
import pandas as pd
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from decimal import Decimal
from dotenv import load_dotenv
import requests


# 환경 변수 로드
load_dotenv()

# ✅ Flask 앱 생성
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_fallback_secret")  # 환경 변수에서 가져오고 없으면 기본값 사용

@app.route("/check-ip")
def check_ip():
    try:
        my_ip = requests.get("https://api64.ipify.org?format=json").json()["ip"]
        return f"🚀 Railway 서버의 현재 외부 IP: {my_ip}"
    except Exception as e:
        return f"❌ IP 확인 실패: {e}"


DBHOST = os.environ.get("DBHOST")
DBNAME = os.environ.get("DBNAME")
DBUSER = os.environ.get("DBUSER")
DBPASSWORD = os.environ.get("DBPASSWORD")

# DB 연결 정보가 없을 경우 오류 출력
if not all([DBHOST, DBNAME, DBUSER, DBPASSWORD]):
    raise ValueError("❌ 환경 변수(DBHOST, DBNAME, DBUSER, DBPASSWORD)가 설정되지 않았습니다!")

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"Server=tcp:{DBHOST},1433;"
    f"DATABASE={DBNAME};"
    f"UID={DBUSER};"
    f"PWD={DBPASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=30;"
)

# ✅ ODBC 드라이버 확인
print("🔍 Checking available ODBC drivers in Python...")
print(pyodbc.drivers())

# ✅ 데이터베이스 연결 확인
def get_db_connection():
    try:
        conn = pyodbc.connect(conn_str)
        print("✅ Successfully connected to the database!")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")  # 로그 출력 추가
        return None  # DB 연결 실패 시 None 반환



# ✅ 사용자 계정 로드 함수
def load_users_from_env():
    users_str = os.getenv("USERS", "")
    users = {}
    if users_str:
        for pair in users_str.split(","):
            username, password = pair.split(":")
            users[username.strip()] = password.strip()
    return users

# ✅ 사용자 계정 로드
users = load_users_from_env()
print("Loaded users:", users)  # 🚀 배포 후 "View Logs"에서 확인

# ✅ Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ✅ 사용자 모델
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id in users else None

# ✅ 로그인 페이지
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for("dashboard"))  # ✅ 로그인 성공 시 대시보드로 이동
        else:
            return "❌ 로그인 실패! 잘못된 아이디 또는 비밀번호", 401  # Unauthorized

    return render_template("login.html")

# ✅ 로그아웃 기능
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ✅ 🚀 Railway 배포 테스트를 위한 홈 페이지 (로그인 필요 없음)
@app.route("/")
def home():
    return "✅ Flask app is running! 🚀"


# ✅ 대시보드 (로그인 필요)
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        site_code = request.form.get("site_code")
        if site_code:
            data = query_database(site_code)
            return render_template("index.html", data=data)
    return render_template("index.html")

# ✅ 데이터 조회 함수
def query_database(site_code):
    """현장코드별 요약 정보, 자재비, 부자재비, 현장상세조회 데이터를 조회"""
    conn = get_db_connection()
    if conn is None:
        return None

    with conn:
        # ✅ 1. 요약 정보 조회
        query_summary = """
            SELECT SiteCode, SiteName, Quantity, ContractAmount 
            FROM SiteInfo WHERE SiteCode = ?
        """
        df_summary = pd.read_sql(query_summary, conn, params=[site_code])
        df_summary = df_summary.iloc[0].to_dict() if not df_summary.empty else {}

        # ✅ 2. 자재비 조회
        query_material = """
            SELECT s.TGType, SUM(s.ShipmentQuantity) AS TotalQuantity, 
                   SUM(s.ShipmentQuantity * u.Price) AS TotalAmount,
                   MIN(s.Month) AS StartMonth, MAX(s.Month) AS EndMonth
            FROM ShipmentStatus s
            JOIN UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
            WHERE s.SiteCode = ?
            GROUP BY s.TGType
        """
        df_material = pd.read_sql(query_material, conn, params=[site_code])

        material_total_quantity = df_material["TotalQuantity"].sum() if not df_material.empty else 0
        material_total_amount = df_material["TotalAmount"].sum() if not df_material.empty else 0
        material_start_month = df_material["StartMonth"].min() if not df_material.empty else None
        material_end_month = df_material["EndMonth"].max() if not df_material.empty else None

        # ✅ 3. 부자재비 조회
        query_submaterial = """
            SELECT SubmaterialType, SUM(Quantity) AS TotalQuantity, 
                   SUM(Amount) AS TotalAmount, AVG(SubPrice) AS AvgPrice,
                   MIN(Month) AS StartMonth, MAX(Month) AS EndMonth
            FROM ExecutionStatus
            WHERE SiteCode = ?
            GROUP BY SubmaterialType
        """
        df_submaterial = pd.read_sql(query_submaterial, conn, params=[site_code])

        # ✅ 4. 현장상세조회
        query_details = """
            SELECT s.SiteCode, s.TGType, s.Month, s.ShipmentQuantity, 
                   u.Price, (s.ShipmentQuantity * u.Price) AS Amount
            FROM ShipmentStatus s
            LEFT JOIN UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
            WHERE s.SiteCode = ?
            ORDER BY s.Month, s.TGType
        """
        df_details = pd.read_sql(query_details, conn, params=[site_code])

    return {
        "summary": df_summary,
        "material": df_material.to_dict("records"),
        "material_total": {
            "total_quantity": material_total_quantity,
            "total_amount": material_total_amount,
            "start_month": material_start_month,
            "end_month": material_end_month
        },
        "submaterial": df_submaterial.to_dict("records"),
        "details": df_details.to_dict("records")
    }
