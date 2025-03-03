from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyodbc
import pandas as pd
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_session import Session  # Flask-Session 추가
from dotenv import load_dotenv

# ✅ 환경 변수 로드
load_dotenv()

# ✅ Flask 앱 생성
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_fallback_secret")

# ✅ Flask-Session 설정
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)

@app.route("/check-db")
def check_db():
    try:
        conn = get_db_connection()
        if conn:
            return "✅ DB 연결 성공!"
        else:
            return "❌ DB 연결 실패: 연결이 None입니다."
    except Exception as e:
        return f"❌ DB 연결 오류: {e}"
@app.route("/test-db-connection")
def test_db_connection():
    import pyodbc
    DBHOST = os.getenv("DBHOST")
    DBNAME = os.getenv("DBNAME")
    DBUSER = os.getenv("DBUSER")
    DBPASSWORD = os.getenv("DBPASSWORD")

    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={DBHOST},1433;"
        f"DATABASE={DBNAME};"
        f"UID={DBUSER};"
        f"PWD={DBPASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=YES;"
        "Connection Timeout=30;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        return "✅ DB 연결 성공! 🎉"
    except Exception as e:
        return f"❌ DB 연결 실패: {str(e)}"


# ✅ DB 연결 정보 가져오기
DBHOST = os.getenv("DBHOST")
DBNAME = os.getenv("DBNAME")
DBUSER = os.getenv("DBUSER")
DBPASSWORD = os.getenv("DBPASSWORD")

if not all([DBHOST, DBNAME, DBUSER, DBPASSWORD]):
    raise ValueError("❌ 환경 변수(DBHOST, DBNAME, DBUSER, DBPASSWORD)가 설정되지 않았습니다.")

# ✅ MSSQL 연결 설정
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

def get_db_connection():
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

# ✅ 로그인 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id in users else None

# ✅ 사용자 계정 로드 함수
def load_users_from_env():
    users_str = os.getenv("USERS", "")
    return {pair.split(":")[0].strip(): pair.split(":")[1].strip() for pair in users_str.split(",")} if users_str else {}

users = load_users_from_env()

# ✅ 기본 페이지 (대시보드로 이동)
@app.route("/")
def home():
    return redirect(url_for("dashboard"))

# ✅ 로그인 & 로그아웃
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            login_user(User(username))
            return redirect(url_for("dashboard"))
        return "❌ 로그인 실패! 잘못된 아이디 또는 비밀번호", 401
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ✅ 대시보드 라우트
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        site_code = request.form.get("site_code")
        if not site_code:
            return render_template("index.html", error="❌ 현장코드를 입력하세요.")

        site_code = site_code.strip()
        data = query_database(site_code)
        session["data"] = data  # ✅ 세션에 데이터 저장

        if "error" in data:
            return render_template("index.html", error=data["error"])

        return redirect(url_for("result"))  # ✅ 결과 페이지로 이동

    return render_template("index.html")  # ✅ GET 요청 시 기본 페이지 유지


# ✅ 결과 페이지
@app.route("/result")
@login_required
def result():
    data = session.get("data", None)
    if not data:
        return redirect(url_for("dashboard"))
    return render_template("result.html", data=data)

# ✅ 데이터 조회 함수
def query_database(site_code):
    conn = get_db_connection()
    if conn is None:
        return {"error": "DB 연결 실패!"}

    try:
        with conn:
            query_summary = f"""
                SELECT SiteCode, SiteName, Quantity, ContractAmount 
                FROM dbo.SiteInfo 
                WHERE SiteCode = N'{site_code}'
            """
            df_summary = pd.read_sql(query_summary, conn)

            if df_summary.empty:
                return {"error": f"❌ '{site_code}'에 해당하는 데이터 없음."}

            return {
                "summary": df_summary.to_dict("records")
            }
    except Exception as e:
        return {"error": str(e)}

# ✅ 500 Internal Server Error 핸들링
@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": str(e)}), 500

# ✅ Flask 실행 (로컬 실행 시 필요)
if __name__ == "__main__":
    app.run(debug=True)


# 웹브라우저에 디버그 표시
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "false").lower() == "true"    

def query_database(site_code):
    """현장코드별 데이터 조회"""
    conn = get_db_connection()
    if conn is None:
        return {"error": "DB 연결 실패!"}

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
                       AVG(u.Price) AS AvgPrice,
                       SUM(s.ShipmentQuantity * u.Price) AS TotalAmount,
                       MIN(s.Month) AS StartMonth,
                       MAX(s.Month) AS EndMonth
                FROM dbo.ShipmentStatus s
                JOIN dbo.UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
                WHERE s.SiteCode = N'{site_code}'
                GROUP BY s.TGType
            """
            df_material = pd.read_sql(query_material, conn)

            # ✅ 3. 부자재비 조회
            query_submaterial = f"""
                SELECT SubmaterialType, SUM(Quantity) AS TotalQuantity, 
                       AVG(SubPrice) AS AvgPrice,
                       SUM(Amount) AS TotalAmount,
                       MIN(Month) AS StartMonth,
                       MAX(Month) AS EndMonth
                FROM dbo.ExecutionStatus
                WHERE SiteCode = N'{site_code}'
                GROUP BY SubmaterialType
            """
            df_submaterial = pd.read_sql(query_submaterial, conn)

            # ✅ 4. 현장 상세조회 (수정된 쿼리)
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
                print("❌ 현장 상세조회 실패: 결과 없음.")
            else:
                print(f"✅ 현장 상세조회 성공: {df_details.to_dict()}")  # ✅ 데이터 출력

            return {
                "summary": df_summary.to_dict("records"),
                "material": df_material.to_dict("records"),
                "submaterial": df_submaterial.to_dict("records"),
                "details": df_details.to_dict("records"),  # ✅ 상세조회 데이터 포함
            }
    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(f"❌ 데이터 조회 오류: {error_message}")
        return {"error": str(e)}


# 🚀 500 Internal Server Error 핸들링 (오류 메시지를 JSON으로 반환)
@app.errorhandler(500)
def internal_server_error(e):
    import traceback
    error_message = traceback.format_exc()  # 전체 오류 스택 추적
    print(f"❌ Internal Server Error: {error_message}")  # 콘솔에도 출력
    return jsonify({"error": str(e), "traceback": error_message}), 500 