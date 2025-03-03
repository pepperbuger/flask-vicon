#!/bin/bash
echo "Installing ODBC dependencies..."
apt-get update
apt-get install -y unixodbc unixodbc-dev

echo "Checking Python & Gunicorn installation..."
python --version
gunicorn --version

echo "Starting the Gunicorn server..."
PORT=${PORT:-8080}
exec gunicorn -w 2 -b 0.0.0.0:$PORT app:app --timeout 120 --log-level=debug --capture-output --error-logfile - --access-logfile -
