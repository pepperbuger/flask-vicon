from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc
import pandas as pd
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from decimal import Decimal
from dotenv import load_dotenv
# Flask-Login과 최신 Werkzeug 호환성 문제 해결
import werkzeug

load_dotenv()  # .env 파일 로드


# ✅ Environment variables setup
DBHOST = os.environ.get("DBHOST", "MISSING_DBHOST")
DBNAME = os.environ.get("DBNAME", "MISSING_DBNAME")
DBUSER = os.environ.get("DBUSER", "MISSING_DBUSER")
DBPASSWORD = os.environ.get("DBPASSWORD", "MISSING_DBPASSWORD")
USERS = os.environ.get("USERS", "MISSING_USERS")

# ✅ Connection string setup
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


# ✅ 환경 변수 값 확인
print(f"🔍 DBHOST: {DBHOST}")
print(f"🔍 DBNAME: {DBNAME}")
print(f"🔍 DBUSER: {DBUSER}")
print(f"🔍 USERS: {USERS}")

try:
    conn = pyodbc.connect(conn_str)
    print("✅ Successfully connected to the database!")
except Exception as e:
    print("❌ Database connection failed:", e)
    conn = None  # 🚨 연결 실패 시 None으로 설정



# ✅ 설치된 ODBC 드라이버 목록 확인
print("🔍 Checking available ODBC drivers in Python...")
print(pyodbc.drivers())  # 설치된 ODBC 드라이버 목록 출력

# ✅ 환경 변수 확인
print("🔍 Loaded USERS:", repr(os.getenv("USERS")))  # 🚀 USERS 값 확인
print("🔍 All ENV Variables:", os.environ)  # 🚀 실행 환경에서 모든 환경 변수 출력


# ✅ Flask 설정
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_fallback_secret")  # 환경 변수에서 가져오고, 없으면 기본값 사용

# ✅ 환경 변수 확인 로그
print("Loaded USERS:", os.getenv("USERS"))
print("Checking ODBC drivers...")
os.system("odbcinst -q -d")

# ✅ 현재 실행 중인 환경 변수 출력 (디버깅)
print("All ENV Variables:", os.environ)  # 🚀 모든 환경 변수를 출력해서 USERS가 포함되었는지 확인

@app.route("/dashboard")
@login_required
def index():
    return render_template('index.html')


# ✅ 사용자 계정 로드 함수
def load_users_from_env():
    users_str = os.getenv("USERS", "")  # 환경 변수에서 USERS 가져오기
    users = {}  # 빈 딕셔너리 생성

    if users_str:
        # "vicon:0304,sungji:0304,admin:admin123" -> {'vicon': '0304', 'sungji': '0304', 'admin': 'admin123'}
        for pair in users_str.split(","):
            username, password = pair.split(":")
            users[username.strip()] = password.strip()  # 양쪽 공백 제거 후 저장
    return users

# ✅ .env에서 불러온 사용자 계정 적용
users = load_users_from_env()

# ✅ users 딕셔너리가 올바르게 만들어졌는지 확인
print("Loaded users:", users)  # 🚀 배포 후 "View Logs"에서 확인

# ✅ Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ✅ 사용자 관리 (간단한 예제)
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# ✅ 로그인 가능한 사용자 목록 (팀원 ID 등록)
def load_users_from_env():
    users_str = os.getenv("USERS", "")  # .env에서 USERS 환경 변수 가져오기
    users = {}  # 빈 딕셔너리 생성

    if users_str:
        for pair in users_str.split(","):
            parts = pair.split(":")
            if len(parts) == 2:
                username, password = parts
                users[username.strip()] = password.strip()

    print("Parsed USERS dict:", users)  # 🚀 변환된 딕셔너리 확인
    return users


@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id in users else None

# ✅ 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 로그인 검증
        if username in users and users[username] == password:
            user = User(username)
            login_user(user)  # 세션에 사용자 정보 저장
            return redirect(url_for('index'))  # 로그인 성공 시 조회 페이지로 이동
        else:
            return "❌ 로그인 실패! 잘못된 아이디 또는 비밀번호", 401  # Unauthorized

    return render_template('login.html')

# ✅ 로그아웃 기능
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


def get_db_connection():
    try:
        return pyodbc.connect(conn_str)
    except Exception as e:
        print("❌ Database connection failed:", e)
        return None  # 연결 실패 시 None 반환

@app.route("/")
def home():
    conn = get_db_connection()
    if conn is None:
        return "❌ Database connection failed", 500
    return "Hello, Railway! 🚀"


# ✅ 데이터 조회 함수 (기존 코드 유지)
def query_database(site_code):
    """현장코드별 요약 정보, 자재비, 부자재비, 현장상세조회 데이터를 조회"""

    with pyodbc.connect(conn_str) as conn:
        
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

        material_total_quantity = df_material['TotalQuantity'].sum() if not df_material.empty else 0
        material_total_amount = df_material['TotalAmount'].sum() if not df_material.empty else 0
        material_start_month = df_material['StartMonth'].min() if not df_material.empty else None
        material_end_month = df_material['EndMonth'].max() if not df_material.empty else None

        # ✅ 3. 부자재비 조회 (빈 값 방지)
        query_submaterial = """
            SELECT SubmaterialType, SUM(Quantity) AS TotalQuantity, 
                   SUM(Amount) AS TotalAmount, AVG(SubPrice) AS AvgPrice,
                   MIN(Month) AS StartMonth, MAX(Month) AS EndMonth
            FROM ExecutionStatus
            WHERE SiteCode = ?
            GROUP BY SubmaterialType
        """
        df_submaterial = pd.read_sql(query_submaterial, conn, params=[site_code])

        # **데이터가 없는 경우 빈 리스트 반환**
        if df_submaterial.empty:
            df_submaterial = pd.DataFrame(columns=['SubmaterialType', 'TotalQuantity', 'TotalAmount', 'AvgPrice', 'StartMonth', 'EndMonth'])

        submaterial_total_quantity = df_submaterial['TotalQuantity'].sum() if not df_submaterial.empty else 0
        submaterial_total_amount = df_submaterial['TotalAmount'].sum() if not df_submaterial.empty else 0
        submaterial_start_month = df_submaterial['StartMonth'].min() if not df_submaterial.empty else None
        submaterial_end_month = df_submaterial['EndMonth'].max() if not df_submaterial.empty else None

        # ✅ 4. 현장상세조회 (빈 값 방지)
        query_details = """
            SELECT s.SiteCode, s.TGType, s.Month, s.ShipmentQuantity, 
                   u.Price, (s.ShipmentQuantity * u.Price) AS Amount
            FROM ShipmentStatus s
            LEFT JOIN UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
            WHERE s.SiteCode = ?
            ORDER BY s.Month, s.TGType
        """
        df_details = pd.read_sql(query_details, conn, params=[site_code])

        if df_details.empty:
            df_details = pd.DataFrame(columns=['SiteCode', 'TGType', 'Month', 'ShipmentQuantity', 'Price', 'Amount'])

    # ✅ 데이터 포맷 정리
    return {
        'summary': df_summary,
        'material': df_material.to_dict('records'),
        'material_total': {
            'total_quantity': material_total_quantity,
            'total_amount': material_total_amount,
            'start_month': material_start_month,
            'end_month': material_end_month
        },
        'submaterial': df_submaterial.to_dict('records'),
        'submaterial_total': {
            'total_quantity': submaterial_total_quantity,
            'total_amount': submaterial_total_amount,
            'start_month': submaterial_start_month,
            'end_month': submaterial_end_month
        },
        'details': df_details.to_dict('records')
    }

# ✅ **조회 페이지 (로그인한 사용자만 접근 가능)**
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        site_code = request.form.get('site_code')
        if site_code:
            data = query_database(site_code)
            return render_template('index.html', data=data)
    return render_template('index.html')



@app.route("/")
def home():
    return "Hello, Railway!"

# 🚀 Gunicorn이 실행될 때 app 객체를 직접 실행


