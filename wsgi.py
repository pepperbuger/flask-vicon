from app import app

if __name__ == "__main__":
    from waitress import serve
    import os

    port = int(os.environ.get("PORT", 8080))  # Railway에서 할당된 포트 사용
    print(f"🚀 Starting Waitress on port {port}...")
    serve(app, host="0.0.0.0", port=port)
