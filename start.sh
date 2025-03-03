#!/bin/bash
echo "🚀 Starting production server with Waitress..."

# Railway에서 자동으로 할당한 포트 사용
PORT=${PORT:-5001}
echo "🚀 Using PORT: ${PORT}"

# ✅ 올바른 Waitress 실행 방식
exec waitress-serve --port=$PORT app:app
 --log-level debug
