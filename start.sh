#!/bin/bash
echo "🚀 Starting production server with Waitress..."
echo "🚀 Using PORT: ${PORT}"  # 포트가 올바르게 설정되는지 확인

export FLASK_APP=wsgi.py
export FLASK_DEBUG=true  # 디버깅 활성화 (일시적으로)
export FLASK_RUN_PORT=${PORT}  # Flask에서 Railway 포트를 직접 사용

# Waitress 실행 (포트가 5000으로 잘못 설정될 경우 대비해 명확하게 지정)
exec waitress-serve --host 0.0.0.0 --port=${PORT} wsgi:app
