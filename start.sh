#!/bin/bash

echo "🔧 Installing ODBC dependencies..."
apt-get update && apt-get install -y unixodbc unixodbc-dev

# ODBC 드라이버가 제대로 설치되었는지 확인
echo "🔍 Checking installed ODBC drivers..."
odbcinst -q -d

echo "🚀 Starting Gunicorn server..."
gunicorn -w 1 -b 0.0.0.0:8080 app:app --timeout 120 --log-level=debug