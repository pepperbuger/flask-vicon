from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import pyodbc
import pandas as pd
import os
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_session import Session  # Flask-Session 추가
from dotenv import load_dotenv
import io
import json
import numpy as np

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

 # 조회기능

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

# store_data
@app.route("/store_data", methods=["POST"])
@login_required
def store_data():
    session["data"] = request.get_json()
    print(f"🔍 [DEBUG] 세션 저장된 데이터: {session['data']}")  # ✅ 로그 추가
    return jsonify({"success": True})


# ✅ 대시보드 페이지 
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


# ✅ 대시보드 데이터 API (차트용 데이터 제공)

@app.route("/dashboard_data")
def dashboard_data():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "DB 연결 실패!"})

    try:
        query = """
            WITH MonthlyShipment AS (
    SELECT 
        Month, 
        SUM(ShipmentQuantity) AS TotalShipment
    FROM ShipmentStatus
    WHERE Month >= FORMAT(DATEADD(MONTH, -11, GETDATE()), 'yyyy-MM')
    GROUP BY Month
),
CategoryShipment AS (
    SELECT 
        Month, 
        CAST(
            CASE 
                WHEN SiteCode LIKE '%(DA)' THEN N'대리점, 유통'
                WHEN SiteCode LIKE '%(DS)' THEN N'납품'
                WHEN SiteCode LIKE '%(KD)' OR SiteCode LIKE '%(DP)' THEN N'조달청'
                WHEN SiteCode LIKE '%(DC)' OR SiteCode LIKE '%(D)' THEN N'공사'
                ELSE N'기타'
            END AS NVARCHAR(100)
        ) AS Category,
        SUM(ShipmentQuantity) AS CategoryShipment
    FROM ShipmentStatus
    WHERE Month >= FORMAT(DATEADD(MONTH, -11, GETDATE()), 'yyyy-MM')
    GROUP BY Month, 
        CAST(
            CASE 
                WHEN SiteCode LIKE '%(DA)' THEN N'대리점, 유통'
                WHEN SiteCode LIKE '%(DS)' THEN N'납품'
                WHEN SiteCode LIKE '%(KD)' OR SiteCode LIKE '%(DP)' THEN N'조달청'
                WHEN SiteCode LIKE '%(DC)' OR SiteCode LIKE '%(D)' THEN N'공사'
                ELSE N'기타'
            END AS NVARCHAR(100)
        )
)
SELECT 
    m.Month, 
    COALESCE(m.TotalShipment, 0) AS TotalShipment,  -- ✅ 출고량이 NULL이면 0으로 처리
    c.Category, 
    COALESCE(c.CategoryShipment, 0) AS CategoryShipment,
    COALESCE((c.CategoryShipment * 100.0 / NULLIF(m.TotalShipment, 0)), 0) AS Percentage
FROM MonthlyShipment m
LEFT JOIN CategoryShipment c ON m.Month = c.Month
ORDER BY m.Month DESC, c.CategoryShipment DESC;

        """

        df = pd.read_sql_query(query, conn)
        df["Category"] = df["Category"].astype(str)  # ✅ 한글 깨짐 방지

        # ✅ 데이터 가공 (UTF-8 인코딩)
        grouped_data = {}
        for _, row in df.iterrows():
            month = row["Month"]
            category = row["Category"]
            total_shipment = row["TotalShipment"]
            category_shipment = row["CategoryShipment"]
            percentage = row["Percentage"]

            if month not in grouped_data:
                grouped_data[month] = {
                    "TotalShipment": total_shipment,  # ✅ 출고량이 JSON에 포함됨
                    "CategoryBreakdown": {}
                }

            grouped_data[month]["CategoryBreakdown"][category] = {
                "Shipment": category_shipment,
                "Percentage": round(percentage, 2)
            }

        return json.dumps({"shipment_trend": grouped_data}, ensure_ascii=False), 200, {'Content-Type': 'application/json; charset=utf-8'}

    except Exception as e:
        return jsonify({"error": f"쿼리 실행 오류: {str(e)}"})

    finally:
        conn.close()  # ✅ 데이터베이스 연결 닫기


# ✅ 조회 결과 페이지
@app.route("/result")
@login_required
def result():
    data = session.get("data", None)
    if not data:
        return jsonify({"error": "세션에 데이터가 없습니다. 다시 검색하세요."}), 400

    # 진행률 계산
    progress_data = calculate_project_progress(
        data['summary'],
        data.get('material', []),
        data.get('submaterial', [])
    )
    
    # 데이터 딕셔너리에 진행률 정보 추가
    data.update({
        'progress': progress_data['overall_progress'],
        'quantity_progress': progress_data['quantity_progress'],
        'cost_progress': progress_data['cost_progress'],
        'total_shipment': progress_data['total_shipment'],
        'total_cost': progress_data['total_cost']
    })

    return render_template("result.html", data=data)

# ✅ 데이터 조회 함수

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

            # ✅ 월별 출고량 데이터 조회
            query_monthly = f"""
                SELECT Month, SUM(ShipmentQuantity) as MonthlyShipment
                FROM dbo.ShipmentStatus
                WHERE SiteCode = N'{site_code}'
                GROUP BY Month
                ORDER BY Month
            """
            df_monthly = pd.read_sql(query_monthly, conn)

            # ✅ TG타입별 물량 분포 데이터
            query_tg_distribution = f"""
                SELECT TGType, SUM(ShipmentQuantity) as TotalQuantity
                FROM dbo.ShipmentStatus
                WHERE SiteCode = N'{site_code}'
                GROUP BY TGType
            """
            df_tg_dist = pd.read_sql(query_tg_distribution, conn)

            # 차트 데이터 준비
            months = df_monthly['Month'].tolist()
            monthly_shipments = df_monthly['MonthlyShipment'].tolist()
            tg_types = df_tg_dist['TGType'].tolist()
            tg_type_quantities = df_tg_dist['TotalQuantity'].tolist()

            # ✅ 월별 단가 데이터 조회
            # 출고량이 가장 많은 TG타입 찾기
            if not df_tg_dist.empty:
                main_tg_type = df_tg_dist.loc[df_tg_dist['TotalQuantity'].idxmax(), 'TGType']
                print(f"✅ 주요 TG타입: {main_tg_type}")
                
                query_monthly_price = f"""
                    SELECT 
                        s.Month,
                        s.TGType,
                        CAST(AVG(CAST(u.Price AS float)) AS float) as AvgPrice
                    FROM dbo.ShipmentStatus s
                    JOIN dbo.UnitPrice u ON s.TGType = u.TGType AND s.Month = u.Month
                    WHERE s.SiteCode = N'{site_code}'
                    AND s.TGType = N'{main_tg_type}'
                    GROUP BY s.Month, s.TGType
                    ORDER BY s.Month
                """
                df_monthly_price = pd.read_sql(query_monthly_price, conn)
                print(f"✅ 월별 단가 데이터 조회 완료 (행 개수: {len(df_monthly_price)})")
                print(f"✅ 단가 데이터: {df_monthly_price['AvgPrice'].tolist()}")
                
                price_data = df_monthly_price['AvgPrice'].tolist() if not df_monthly_price.empty else []
            else:
                main_tg_type = ''
                price_data = []
                print("❌ TG타입 데이터가 없습니다.")

            # 주요 TG타입 단가 데이터셋 준비
            main_tg_price_dataset = {
                'label': f'{main_tg_type} 단가 추이',
                'data': price_data,
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'borderWidth': 2,
                'fill': False,
                'tension': 0.4
            }

            print(f"✅ 차트 데이터셋 준비 완료: {main_tg_price_dataset}")

            return {
                "summary": df_summary.to_dict("records") if not df_summary.empty else [],
                "material": df_material.to_dict("records") if not df_material.empty else [],
                "material_total": material_total,
                "submaterial": df_submaterial.to_dict("records") if not df_submaterial.empty else [],
                "submaterial_total": submaterial_total,
                "details": df_details.to_dict("records") if not df_details.empty else [],
                # 차트 데이터
                "months": months,
                "monthly_shipments": monthly_shipments,
                "tg_types": tg_types,
                "tg_type_quantities": tg_type_quantities,
                "main_tg_price_dataset": main_tg_price_dataset
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

# ✅ 500 Internal Server Error 핸들링
@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": str(e)}), 500

# ✅ Flask 실행 (로컬 실행 시 필요)
if __name__ == "__main__":
    app.run(debug=True)


# 웹브라우저에 디버그 표시
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "false").lower() == "true"    

def calculate_project_progress(summary_data, material_data, submaterial_data):
    """
    프로젝트 전체 진행률을 계산하는 함수
    """
    # 1. 물량 기준 진행률 계산
    contract_quantity = summary_data[0]['Quantity']
    total_shipment_quantity = sum(row['TotalQuantity'] for row in material_data)
    quantity_progress = (total_shipment_quantity / contract_quantity * 100) if contract_quantity > 0 else 0

    # 2. 금액 기준 진행률 계산
    contract_amount = summary_data[0]['ContractAmount']
    total_material_cost = sum(row['TotalAmount'] for row in material_data)
    total_submaterial_cost = sum(row['TotalAmount'] for row in submaterial_data)
    total_cost = total_material_cost + total_submaterial_cost
    cost_progress = (total_cost / contract_amount * 100) if contract_amount > 0 else 0

    # 3. 종합 진행률 계산 (물량과 금액 진행률의 평균)
    overall_progress = (quantity_progress + cost_progress) / 2

    return {
        'overall_progress': round(overall_progress, 1),
        'quantity_progress': round(quantity_progress, 1),
        'cost_progress': round(cost_progress, 1),
        'total_shipment': total_shipment_quantity,
        'total_cost': total_cost
    }    
