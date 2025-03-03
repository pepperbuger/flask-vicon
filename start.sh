#!/bin/bash

echo "🔍 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt


echo "🔍 Installing ODBC dependencies..."
apt-get update
apt-get install -y unixodbc unixodbc-dev curl gnupg
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc > /dev/null
curl -fsSL https://packages.microsoft.com/config/debian/10/prod.list | tee /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17



echo "✅ Checking Python & Gunicorn installation..."
python --version
gunicorn --version

# 🚀 테스트 모드: Flask 직접 실행 (Gunicorn 없이)
if [ "$FLASK_DEBUG" = "true" ]; then
    echo "🔍 Flask 직접 실행 테스트 중..."
    python -m flask run --host=0.0.0.0 --port=8080
else
    echo "🚀 Starting the Gunicorn server..."
    PORT=${PORT:-8080}
    exec gunicorn -w 2 -b 0.0.0.0:$PORT --chdir /app wsgi:app
fi

export FLASK_APP=wsgi.py
export FLASK_ENV=production
