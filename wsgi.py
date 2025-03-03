from app import app
from waitress import serve
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # 기본적으로 환경 변수에서 PORT 가져오기
    print(f"🚀 Starting Waitress on port {port}...")
    serve(app, host="0.0.0.0", port=port, threads=4)
