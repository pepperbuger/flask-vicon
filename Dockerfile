# ✅ 1. Python 3.9 환경을 기반으로 사용
FROM python:3.9

# ✅ MSSQL ODBC 드라이버 설치
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17



# ✅ 2. ODBC 라이브러리 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    odbcinst \
    libodbc1 \
    odbcinst1debian2 \
    curl

# ✅ 3. 작업 디렉토리 설정
WORKDIR /app

# ✅ 4. 프로젝트 코드 복사 (현재 폴더에 있는 모든 파일을 컨테이너로 복사)
COPY . /app

# ✅ 5. Python 패키지 설치 전에 pip 업그레이드 추가
RUN pip install --upgrade pip


# ✅ 6. Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 6. ODBC 드라이버가 정상적으로 설치되었는지 확인 (디버깅용 로그 출력)
RUN ldconfig -p | grep odbc

# ✅ 7. Flask 애플리케이션 실행
CMD ["gunicorn", "-b", "0.0.0.0:5001", "app:app"]