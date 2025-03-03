from app import app  # Flask 앱 가져오기

if __name__ == "__main__":
    # 🚀 이제 `waitress` 실행은 `start.sh`에서 처리하므로 필요 없음
    app.run()  # 로컬 개발용 (Railway 배포에서는 사용되지 않음)
