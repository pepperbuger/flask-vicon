#!/bin/bash
echo "🚀 Starting production server with Waitress..."

# 환경 변수 설정
export FLASK_APP=wsgi.py
export FLASK_ENV=production

# Waitress 실행 (Railway가 할당한 포트 사용)
exec waitress-serve --host 0.0.0.0 --port=${PORT} wsgi:app
