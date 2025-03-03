from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc
import pandas as pd
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from decimal import Decimal
from dotenv import load_dotenv
import requests
import sys  # 🚀 sys 모듈 추가


# ✅ 환경 변수 로드
load_dotenv()

# ✅ Flask 앱 생성
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_fallback_secret")  # 환경 변수에서 가져오고 없으면 기본값 사용

# ✅ 외부 IP 확인
# @app.route("/check-ip")
# def check_ip():
#     try:
#         my_ip = requests.get("https://api64.ipify.org?format=json").json()["ip"]
#         return f"🚀 Railway 서버의 현재 외부 IP: {my_ip}"
#     except Exception as e:
#         return f"❌ IP 확인 실패: {e}"

# ✅ 환경 변수에서 DB 접속 정보 가져오기
DBHOST = os.getenv("DBHOST")
DBNAME = os.getenv("DBNAME")
DBUSER = os.getenv("DBUSER")
DBPASSWORD = os.getenv("DBPASSWORD")

# @app.route("/check-env")
# def check_env():
#     return f"""
#     DBHOST: {DBHOST} <br>
#     DBNAME: {DBNAME} <br>
#     DBUSER: {DBUSER} <br>
#     DBPASSWORD: {"*" * len(DBPASSWORD) if DBPASSWORD else "None"}
#     """

# ✅ 환경 변수가 없을 경우 오류 처리
if not all([DBHOST, DBNAME, DBUSER, DBPASSWORD]):
    raise ValueError("❌ 환경 변수(DBHOST, DBNAME, DBUSER, DBPASSWORD)가 설정되지 않았습니다.")

# ✅ ODBC 연결 문자열 (MSSQL 연결)
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={DBHOST},1433;"
    f"DATABASE={DBNAME};"
    f"UID={DBUSER};"
    f"PWD={DBPASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=30;"
)

# ✅ DB 연결 함수
def get_db_connection():
    try:
        print("🔍 Checking database connection...")
        conn = pyodbc.connect(conn_str)
        print("✅ Successfully connected to the database!")
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None  # DB 연결 실패 시 None 반환

# ✅ ODBC 드라이버 확인
@app.route("/check-odbc")
def check_odbc():
    return f"Available ODBC Drivers: {pyodbc.drivers()}"

# ✅ DB 연결 테스트 엔드포인트
@app.route("/check-db")
def check_db():
    try:
        print("🔍 Checking database connection...")
        conn = get_db_connection()
        if conn:
            print("✅ DB 연결 성공!")
            return "✅ DB 연결 성공!"
        else:
            print("❌ DB 연결 실패: 연결이 None입니다.")
            return "❌ DB 연결 실패: 연결이 None입니다."
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return f"❌ Database connection failed: {e}"


# ✅ 사용자 계정 로드 함수
def load_users_from_env():
    users_str = os.getenv("USERS", "")
    users = {pair.split(":")[0].strip(): pair.split(":")[1].strip() for pair in users_str.split(",")} if users_str else {}
    return users

# ✅ 사용자 계정 로드
users = load_users_from_env()
print("Loaded users:", users)  # 🚀 배포 후 "View Logs"에서 확인

# ✅ Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id in users else None

# ✅ 로그인 & 로그아웃 엔드포인트
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            login_user(User(username))
            return redirect(url_for("dashboard"))  # ✅ 로그인 성공 시 대시보드로 이동
        return "❌ 로그인 실패! 잘못된 아이디 또는 비밀번호", 401  # Unauthorized
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ✅ 기본 페이지 (로그인 필요 없음)
@app.route("/")
def home():
    # 사용자가 로그인하지 않았다면 로그인 페이지로 리디렉션
    if "user_id" not in session:
        return redirect(url_for("login"))  # 🚀 로그인 페이지로 이동
    return redirect(url_for("dashboard"))  # 🚀 로그인된 사용자는 대시보드로 이동

# ✅ 대시보드 (로그인 필요)
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    data = None  # 🔹 데이터를 유지하기 위한 변수

    if request.method == "POST":
        site_code = request.form.get("site_code")
        print(f"🔍 입력된 현장코드 (원본): '{site_code}'")  

        if not site_code:
            return render_template("index.html", error="❌ 현장코드를 입력하세요.")

        site_code = site_code.strip()  

        print(f"🔍 변환된 site_code: '{site_code}'")  

        data = query_database(site_code)
        
        # ✅ JSON 데이터 형식인지 확인
        if isinstance(data, tuple):
            data = data[0]  # 튜플이면 첫 번째 요소만 사용

        if "error" in data:
            return render_template("index.html", error=data["error"])  

    # 🔹 데이터가 None이 아닐 경우 유지하면서 렌더링
    return render_template("index.html", data=data)


# ✅ 데이터 조회 함수
from flask import jsonify  # JSON 응답을 위한 모듈 추가
@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": str(e)}), 500

# 웹브라우저에 디버그 표시
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "false").lower() == "true"    

def query_database(site_code):
    """현장코드별 데이터 조회"""
    conn = get_db_connection()
    if conn is None:
        return {"error": "DB 연결 실패!"}  # 🚀 튜플이 아닌 딕셔너리로 반환

    try:
        with conn:
            print(f"🔍 DB에서 조회 중: SiteCode='{site_code}'")

            # ✅ 1. 요약 정보 조회
            query_summary = f"""
                SELECT SiteCode, SiteName, Quantity, ContractAmount 
                FROM dbo.SiteInfo 
                WHERE SiteCode = N'{site_code}'
            """
            df_summary = pd.read_sql(query_summary, conn)

            if df_summary.empty:
                return {"error": f"❌ '{site_code}'에 해당하는 데이터 없음."}  

            # ✅ 2. 자재비 조회
            query_material = f"""
                SELECT s.TGType, SUM(s.ShipmentQuantity) AS TotalQuantity, 
                       SUM(s.ShipmentQuantity * u.Price) AS TotalAmount
                FROM dbo.ShipmentStatus s
                JOIN dbo.UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
                WHERE s.SiteCode = N'{site_code}'
                GROUP BY s.TGType
            """
            df_material = pd.read_sql(query_material, conn)

            # ✅ 3. 부자재비 조회
            query_submaterial = f"""
                SELECT SubmaterialType, SUM(Quantity) AS TotalQuantity, 
                       SUM(Amount) AS TotalAmount, AVG(SubPrice) AS AvgPrice
                FROM dbo.ExecutionStatus
                WHERE SiteCode = N'{site_code}'
                GROUP BY SubmaterialType
            """
            df_submaterial = pd.read_sql(query_submaterial, conn)

            # ✅ 4. 현장상세조회
            query_details = f"""
                SELECT s.SiteCode, s.TGType, s.Month, s.ShipmentQuantity, 
                       u.Price, (s.ShipmentQuantity * u.Price) AS Amount
                FROM dbo.ShipmentStatus s
                LEFT JOIN dbo.UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
                WHERE s.SiteCode = N'{site_code}'
                ORDER BY s.Month, s.TGType
            """
            df_details = pd.read_sql(query_details, conn)

            if df_details.empty:
                print("❌ 현장상세조회 실패: 결과 없음.")
            else:
                print(f"✅ 현장상세조회 성공: {df_details.to_dict()}")

    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(f"❌ 데이터 조회 오류: {error_message}")
        return {"error": str(e), "traceback": error_message}  

    return {
        "summary": df_summary.to_dict("records"),
        "material": df_material.to_dict("records"),
        "submaterial": df_submaterial.to_dict("records"),
        "details": df_details.to_dict("records")
    }


# 🚀 500 Internal Server Error 핸들링 (오류 메시지를 JSON으로 반환)
@app.errorhandler(500)
def internal_server_error(e):
    import traceback
    error_message = traceback.format_exc()  # 전체 오류 스택 추적
    print(f"❌ Internal Server Error: {error_message}")  # 콘솔에도 출력
    return jsonify({"error": str(e), "traceback": error_message}), 500
