import os
import io
import numpy as np
import pandas as pd
import pyodbc
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = "your_secret_key"

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

    # ✅ int64 → int 변환 (NumPy int64 타입을 일반 int로 변환)
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
    print(f"🔍 [DEBUG] 세션에 저장된 데이터: {session['data']}")  # ✅ 로그 추가
    return jsonify({"success": True})

# ✅ 조회 결과 페이지
@app.route("/result")
@login_required
def result():
    data = session.get("data", None)
    if not data:
        return jsonify({"error": "세션에 데이터가 없습니다. 다시 검색하세요."}), 400

    return render_template("result.html", data=data)

# ✅ 데이터 조회 함수 (예외 처리 강화)
def query_database(site_code):
    conn = get_db_connection()
    if conn is None:
        return {"error": "DB 연결 실패!"}

    try:
        with conn:
            print(f"🔍 DB에서 조회 중: SiteCode='{site_code}'")

            # ✅ 1. 요약 정보 조회
            query_summary = f"SELECT SiteCode, SiteName, Quantity, ContractAmount FROM dbo.SiteInfo WHERE SiteCode = N'{site_code}'"
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

# ✅ Flask 실행
if __name__ == "__main__":
    app.run(debug=True)
