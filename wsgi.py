from app import app
from waitress import serve
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway에서 할당된 포트 사용
    print(f"🚀 Starting Waitress on port {port}...")
    serve(app, host="0.0.0.0", port=port, threads=4)  # 다중 쓰레드 처리 추가
