# ✅ 1. Python 3.9 환경 기반
FROM python:3.9

# ✅ MSSQL ODBC 드라이버 설치
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc unixodbc-dev

RUN odbcinst -q -d

# ✅ 3. ODBC 드라이버 설정
ENV ODBCINI=/etc/odbc.ini
ENV ODBCSYSINI=/etc
ENV LD_LIBRARY_PATH=/opt/microsoft/msodbcsql17/lib64:/usr/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# ✅ 4. 작업 디렉토리 설정
WORKDIR /app

# ✅ 5. 프로젝트 파일 복사
COPY . /app

# ✅ 6. Python 패키지 설치 전에 pip 업그레이드
RUN pip install --upgrade pip

# ✅ 7. requirements.txt 먼저 복사 후 설치 (캐싱 최적화)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 8. ODBC 드라이버 정상 설치 확인
RUN odbcinst -q -d && ldconfig -p | grep odbc

# ✅ 9. Gunicorn 실행을 위한 포트 설정
EXPOSE 8080

# ✅ 10. 컨테이너 실행 시 start.sh 실행 (Gunicorn 실행 포함)
CMD ["sh", "start.sh"]
