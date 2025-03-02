#!/bin/bash
echo "Installing ODBC dependencies..."
apt-get update;
apt-get install -y unixodbc unixodbc-dev;

# ODBC 드라이버 확인
echo "Checking installed ODBC drivers..."
odbcinst -q -d

# 현재 디렉토리 확인
echo "Checking current directory contents..."
ls -la

# app.py 존재 여부 확인
echo "Checking if app.py exists..."
if [ -f "app.py" ]; then
    echo "✅ app.py found"
else
    echo "❌ app.py NOT found!"
    exit 1  # 파일이 없으면 종료
fi

# 환경 변수 확인
echo "🔍 Printing Environment Variables..."
env | grep DB

# Gunicorn 실행
echo "Starting the Gunicorn server with detailed logging..."
PORT=${PORT:-8080}
exec gunicorn -w 2 -b 0.0.0.0:$PORT app:app --timeout 120 --log-level=debug --capture-output --error-logfile - --access-logfile -
