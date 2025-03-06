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

# ✅ MSSQL 연결 설정
DBHOST = "your_db_host"
DBNAME = "your_db_name"
DBUSER = "your_db_user"
DBPASSWORD = "your_db_password"

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={DBHOST},1433;DATABASE={DBNAME};"
    f"UID={DBUSER};PWD={DBPASSWORD};Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;"
)

def get_db_connection():
    try:
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

# ✅ Flask 실행
if __name__ == "__main__":
    app.run(debug=True)

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

users = {"admin": "password"}  # ✅ 예제 사용자

# ✅ 기본 페이지 (대시보드로 이동)
@app.route("/")
def home():
    return redirect(url_for("dashboard"))

# ✅ 검색 기능 (현장 코드 조회)
@app.route("/search", methods=["POST"])
@login_required
def search():
    site_code = request.json.get("site_code", "").strip()
    if not site_code:
        return jsonify({"error": "현장코드를 입력하세요."})

    data = query_database(site_code)

    if "error" in data:
        return jsonify({"error": data["error"]})

    # ✅ NumPy `int64` → Python `int` 변환
    for key in data:
        if isinstance(data[key], list):
            for row in data[key]:
                for k, v in row.items():
                    if isinstance(v, (np.int64, np.float64)):  # ✅ float도 변환
                        row[k] = int(v)

    return jsonify(data)

# ✅ 세션에 데이터 저장 후 `/result`로 이동
@app.route("/store_data", methods=["POST"])
@login_required
def store_data():
    session["data"] = request.get_json()
    print(f"🔍 [DEBUG] 세션 저장된 데이터: {session['data']}")  # ✅ 로그 추가
    return jsonify({"success": True})

# ✅ 조회 결과 페이지
@app.route("/result")
@login_required
def result():
    data = session.get("data", None)
    if not data:
        return jsonify({"error": "세션에 데이터가 없습니다. 다시 검색하세요."}), 400

    return render_template("result.html", data=data)

# ✅ 대시보드 페이지 (조회 기능 추가)
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        site_code = request.form.get("site_code").strip()
        if not site_code:
            return render_template("index.html", error="❌ 현장코드를 입력하세요.")

        data = query_database(site_code)
        session["data"] = data  # ✅ 세션에 데이터 저장
        return redirect(url_for("result"))

    return render_template("dashboard.html")

@app.route("/dashboard_data")
@login_required
def dashboard_data():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "DB 연결 실패!"})

    try:
        with conn:
            # ✅ 1️⃣ 최근 6개월 조회
            recent_months_query = """
                SELECT DISTINCT TOP 6 Month FROM ShipmentStatus ORDER BY Month DESC
            """
            recent_months = pd.read_sql(recent_months_query, conn)['Month'].tolist()

            # ✅ 2️⃣ 월별 출고량 조회
            query_total_shipment = """
                SELECT Month, SUM(ShipmentQuantity) AS TotalShipment
                FROM ShipmentStatus
                WHERE Month IN ({})
                GROUP BY Month
                ORDER BY Month
            """.format(",".join([f"'{m}'" for m in recent_months]))
            df_total_shipment = pd.read_sql(query_total_shipment, conn)

            # ✅ 3️⃣ DA, DC, DS, KD 비율 조회
            query_shipment_ratio = """
                SELECT Month, SiteCode, SUM(ShipmentQuantity) AS Quantity
                FROM ShipmentStatus
                WHERE Month IN ({})
                GROUP BY Month, SiteCode
                ORDER BY Month
            """.format(",".join([f"'{m}'" for m in recent_months]))
            df_shipment_ratio = pd.read_sql(query_shipment_ratio, conn)

            # ✅ SiteCode에서 (DA), (DC), (DS), (KD) 추출하여 그룹화
            df_shipment_ratio['Category'] = df_shipment_ratio['SiteCode'].str.extract(r"\((DA|DS|KD|DC)\)$")
            df_shipment_ratio = df_shipment_ratio.groupby(["Month", "Category"])["Quantity"].sum().reset_index()

            # ✅ 4️⃣ 최근 6개월 단가 추이 조회
            query_price_trend = """
                SELECT Month, AVG(CASE WHEN TGType IN ('M12085(120)', 'M13085(120)') THEN Price END) AS AvgPrice
                FROM UnitPrice
                WHERE Month IN ({})
                GROUP BY Month
                ORDER BY Month
            """.format(",".join([f"'{m}'" for m in recent_months]))
            df_price_trend = pd.read_sql(query_price_trend, conn)

    except Exception as e:
        return jsonify({"error": f"쿼리 실행 오류: {str(e)}"})

    return jsonify({
        "total_shipment": df_total_shipment.to_dict("records"),
        "shipment_ratio": df_shipment_ratio.to_dict("records"),
        "price_trend": df_price_trend.to_dict("records")
    })
    

# ✅ 데이터 조회 함수 (요약정보, 자재비, 부자재비, 상세조회 포함)
def query_database(site_code):
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

            return {
                "summary": df_summary.to_dict("records"),
                "material": df_material.to_dict("records"),
                "submaterial": df_submaterial.to_dict("records"),
            }
    except Exception as e:
        return {"error": f"쿼리 실행 오류: {str(e)}"}

# ✅ 엑셀 다운로드 기능 (빈 데이터 예외 처리)
@app.route("/download_excel")
@login_required
def download_excel():
    data = session.get("data", None)
    if not data:
        return "❌ 데이터가 없습니다.", 400

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        if "summary" in data and data["summary"]:
            pd.DataFrame(data["summary"]).to_excel(writer, sheet_name="요약정보", index=False)
        if "material" in data and data["material"]:
            pd.DataFrame(data["material"]).to_excel(writer, sheet_name="자재비", index=False)
        if "submaterial" in data and data["submaterial"]:
            pd.DataFrame(data["submaterial"]).to_excel(writer, sheet_name="부자재비", index=False)

    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name="현장_조회결과.xlsx")

