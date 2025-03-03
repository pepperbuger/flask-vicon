#!/bin/bash
echo "🚀 Starting production server with Waitress..."
echo "🚀 Using PORT: ${PORT}"

export FLASK_APP=wsgi.py
export FLASK_DEBUG=true  # 디버깅 활성화 (일시적으로)
export FLASK_RUN_PORT=5001  # Railway에서 설정한 포트 사용

# Waitress 실행 (PORT 5001 적용)
exec waitress-serve --host 0.0.0.0 --port=5001 wsgi:app
