#!/bin/bash
echo "🔍 Flask 직접 실행 테스트 중..."

export FLASK_DEBUG=1  # 디버그 모드 활성화
python -m flask run --host=0.0.0.0 --port=8080
