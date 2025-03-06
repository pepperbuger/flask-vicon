from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import pyodbc
import pandas as pd
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_session import Session  # Flask-Session 추가
from dotenv import load_dotenv
import io

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

# 조회기능
@app.route("/search", methods=["POST"])
@login_required
def search():
    data = request.get_json()
    if not data or "site_code" not in data:
        return jsonify({"error": "현장코드를 입력하세요."}), 400  # 🚨 잘못된 요청 방지

    site_code = data["site_code"].strip()
    print(f"🔍 검색 요청된 현장코드: {site_code}")  # ✅ 값 확인

    result_data = query_database(site_code)
    if "error" in result_data:
        return jsonify({"error": result_data["error"]}), 404  # 🚨 데이터 없을 경우 404 반환

    return jsonify(result_data)  # ✅ 정상적으로 JSON 응답 반환



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

# ✅ 대시보드 페이지 
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        site_code = request.form.get("site_code")
        if not site_code:
            return render_template("index.html", error="❌ 현장코드를 입력하세요.")

        site_code = site_code.strip()
        data = query_database(site_code)
        return render_template("index.html", data=data)

    return render_template("index.html")

# store_data
@app.route("/store_data", methods=["POST"])
@login_required
def store_data():
    session["data"] = request.get_json()  # ✅ 세션에 데이터 저장
    return jsonify({"success": True})


# ✅ 대시보드 데이터 API (차트용 데이터 제공)
@app.route("/dashboard_data")
@login_required
def dashboard_data():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "DB 연결 실패!"})

    try:
        with conn:
            recent_months_query = """
                SELECT DISTINCT TOP 6 Month FROM ShipmentStatus ORDER BY Month DESC
            """
            recent_months = pd.read_sql(recent_months_query, conn)['Month'].tolist()

            query_shipment_trend = """
                SELECT SiteCode, Month, SUM(ShipmentQuantity) AS TotalShipment
                FROM ShipmentStatus
                WHERE Month IN ({})
                GROUP BY SiteCode, Month
                ORDER BY Month
            """.format(",".join([f"'{m}'" for m in recent_months]))

            df_shipment_trend = pd.read_sql(query_shipment_trend, conn)

            # ✅ NaN 값 처리
            df_shipment_trend['Category'] = df_shipment_trend['SiteCode'].str.extract(r"\((DA|DS|KD|DC)\)$")
            df_shipment_trend['Category'] = df_shipment_trend['Category'].fillna("기타")  # NaN 처리

            # ✅ 월별 데이터 그룹화
            shipment_trend = df_shipment_trend.groupby(["Month", "Category"])["TotalShipment"].sum().reset_index().to_dict("records")

            if not shipment_trend:
                return jsonify({"error": "출고 데이터 없음"})  # ✅ 데이터 없을 경우 처리

    except Exception as e:
        return jsonify({"error": f"쿼리 실행 오류: {str(e)}"})  # ✅ 오류 처리

    return jsonify({"shipment_trend": shipment_trend})


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
                return {"error": f"❌ '{site_code}'에 해당하는 데이터 없음."}  # ✅ 데이터 없을 때 메시지 추가

            return {
                "summary": df_summary.to_dict("records") if not df_summary.empty else []
            }
    except Exception as e:
        return {"error": f"쿼리 실행 오류: {str(e)}"}  # ✅ 오류 발생 시 상세 메시지 추가

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
            print(f"✅ 요약 데이터 조회 완료 (행 개수: {len(df_summary)})")

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
            print(f"✅ 자재비 데이터 조회 완료 (행 개수: {len(df_material)})")

            # ✅ 자재비 소계 처리 (None 방지)
            material_total = {
                "total_quantity": df_material["TotalQuantity"].sum() if not df_material.empty else 0,
                "total_amount": df_material["TotalAmount"].sum() if not df_material.empty else 0,
                "start_month": df_material["StartMonth"].min() if not df_material.empty else "-",
                "end_month": df_material["EndMonth"].max() if not df_material.empty else "-"
            }

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
            print(f"✅ 부자재비 데이터 조회 완료 (행 개수: {len(df_submaterial)})")

            # ✅ 부자재비 소계 처리 (None 방지)
            submaterial_total = {
                "total_quantity": df_submaterial["TotalQuantity"].sum() if not df_submaterial.empty else 0,
                "total_amount": df_submaterial["TotalAmount"].sum() if not df_submaterial.empty else 0,
                "start_month": df_submaterial["StartMonth"].min() if not df_submaterial.empty else "-",
                "end_month": df_submaterial["EndMonth"].max() if not df_submaterial.empty else "-"
            }

            # ✅ 4. 현장 상세조회
            query_details = f"""
                SELECT s.SiteCode, s.TGType, s.Month, s.ShipmentQuantity, 
                       u.Price, (s.ShipmentQuantity * u.Price) AS Amount
                FROM dbo.ShipmentStatus s
                LEFT JOIN dbo.UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
                WHERE s.SiteCode = N'{site_code}'
                ORDER BY s.Month, s.TGType
            """
            df_details = pd.read_sql(query_details, conn)
            print(f"✅ 현장 상세조회 데이터 조회 완료 (행 개수: {len(df_details)})")

            # ✅ 데이터가 없을 경우 빈 리스트 반환하여 KeyError 방지
            return {
                "summary": df_summary.to_dict("records") if not df_summary.empty else [],
                "material": df_material.to_dict("records") if not df_material.empty else [],
                "material_total": material_total,
                "submaterial": df_submaterial.to_dict("records") if not df_submaterial.empty else [],
                "submaterial_total": submaterial_total,
                "details": df_details.to_dict("records") if not df_details.empty else []
            }
    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(f"❌ 데이터 조회 오류: {error_message}")
        return {"error": str(e)}


# 엑셀생성---

@app.route("/download_excel")
@login_required
def download_excel():
    data = session.get("data", None)
    if not data:
        return "❌ 데이터가 없습니다.", 400

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book

        # ✅ 📌 1. 요약 정보 (현장 정보)
        df_summary = pd.DataFrame(data["summary"])
        df_summary = df_summary.rename(columns={
            "SiteCode": "현장코드",
            "SiteName": "현장명",
            "Quantity": "계약물량 (㎡)",
            "ContractAmount": "계약금액 (원)"
        })
        df_summary.to_excel(writer, sheet_name="요약정보", index=False)

        # ✅ 🏗️ 2. 자재비
        if "material" in data and data["material"]:
            df_material = pd.DataFrame(data["material"])
            df_material = df_material.rename(columns={
                "TGType": "TG타입",
                "TotalQuantity": "수량 (㎡)",
                "AvgPrice": "단가 (원/㎡)",
                "TotalAmount": "금액 (원)",
                "StartMonth": "출고시작월",
                "EndMonth": "출고종료월"
            })

            df_material.to_excel(writer, sheet_name="자재비", index=False)

            # ✅ 소계 추가
            material_total = {
                "TG타입": "소계",
                "수량 (㎡)": df_material["수량 (㎡)"].sum(),
                "단가 (원/㎡)": "-",
                "금액 (원)": df_material["금액 (원)"].sum(),
                "출고시작월": "-",
                "출고종료월": "-"
            }
            df_material = df_material.append(material_total, ignore_index=True)

            df_material.to_excel(writer, sheet_name="자재비", index=False)

        # ✅ 🔩 3. 부자재비
        if "submaterial" in data and data["submaterial"]:
            df_submaterial = pd.DataFrame(data["submaterial"])
            df_submaterial = df_submaterial.rename(columns={
                "SubmaterialType": "타입",
                "TotalQuantity": "수량",
                "AvgPrice": "단가 (원)",
                "TotalAmount": "금액 (원)",
                "StartMonth": "구매시작월",
                "EndMonth": "구매종료월"
            })

            df_submaterial.to_excel(writer, sheet_name="부자재비", index=False)

            # ✅ 소계 추가
            submaterial_total = {
                "타입": "소계",
                "수량": df_submaterial["수량"].sum(),
                "단가 (원)": "-",
                "금액 (원)": df_submaterial["금액 (원)"].sum(),
                "구매시작월": "-",
                "구매종료월": "-"
            }
            df_submaterial = df_submaterial.append(submaterial_total, ignore_index=True)

            df_submaterial.to_excel(writer, sheet_name="부자재비", index=False)

        # ✅ 📌 4. 엑셀 스타일 적용
        for sheet in writer.sheets:
            worksheet = writer.sheets[sheet]
            worksheet.set_column("A:A", 20)  # 첫 번째 컬럼 너비 조정
            worksheet.set_column("B:D", 15)  # 데이터 컬럼 너비 조정
            worksheet.set_column("E:F", 12)  # 날짜 컬럼 너비 조정

    output.seek(0)

    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="현장_조회결과.xlsx")      

# 🚀 500 Internal Server Error 핸들링 (오류 메시지를 JSON으로 반환)
@app.errorhandler(500)
def internal_server_error(e):
    import traceback
    error_message = traceback.format_exc()  # 전체 오류 스택 추적
    print(f"❌ Internal Server Error: {error_message}")  # 콘솔에도 출력
    return jsonify({"error": str(e), "traceback": error_message}), 500 