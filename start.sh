#!/bin/bash
echo "🚀 Starting production server with Waitress..."

# Railway에서 자동으로 할당한 포트 사용
PORT=${PORT:-5001}
echo "🚀 Using PORT: ${PORT}"

# Waitress 실행 (디버그 로그 활성화)
exec python -m waitress --listen=0.0.0.0:$PORT app:app --log-level debug
