#!/bin/bash
echo "Installing ODBC dependencies..."
apt-get update;
apt-get install -y unixodbc unixodbc-dev;

echo "Checking current directory contents..."
ls -la

echo "Checking if app.py exists..."
if [ -f "app.py" ]; then
    echo "app.py found"
else
    echo "app.py NOT found!"
fi

echo "Starting the Gunicorn server with detailed logging..."
PORT=${PORT:-8080}
exec gunicorn -w 2 -b 0.0.0.0:$PORT app:app --timeout 120 --log-level=debug --capture-output --error-logfile - --access-logfile -