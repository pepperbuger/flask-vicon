from flask import Flask, render_template, request
import pyodbc

app = Flask(__name__)

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=ConstructionDB;"
    "Trusted_Connection=yes;"
)

print("✅ MSSQL에 Windows 인증으로 연결되었습니다!")

# ✅ 기본 페이지: 현장코드 입력창
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        site_code = request.form['site_code']
        result = query_database(site_code)
        return render_template('result.html', data=result, site_code=site_code)
    return render_template('index.html')

# ✅ 데이터베이스 쿼리 함수
def query_database(site_code):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    query = """
    SELECT s.SiteCode, s.TGType, s.Month, s.ShipmentQuantity, u.Price, 
           s.ShipmentQuantity * u.Price AS Amount
    FROM ShipmentStatus s
    JOIN UnitPrice u 
    ON s.TGType = u.TGType AND s.Month = u.Month
    WHERE s.SiteCode = ?
    ORDER BY s.Month, s.TGType;
    """
    cursor.execute(query, (site_code,))
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

if __name__ == '__main__':
    app.run(debug=True)
