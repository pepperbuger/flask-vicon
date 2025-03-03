#!/bin/bash
echo "🚀 Starting production server with Waitress..."

# Railway에서 자동으로 할당한 포트 사용
export PORT=${PORT:-5001}
echo "🚀 Using PORT: ${PORT}"

export FLASK_APP=wsgi.py
export FLASK_DEBUG=true  # 디버깅 활성화

# Waitress 실행 (PORT 자동 감지)
exec python wsgi.py
