from app import app
from waitress import serve
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # 기본 포트를 5001로 설정
    print(f"🚀 Starting Waitress on port {port}...")
    serve(app, host="0.0.0.0", port=port, threads=4)
