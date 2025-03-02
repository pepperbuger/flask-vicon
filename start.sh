#!/bin/bash
echo "Installing ODBC dependencies..."
apt-get update;
apt-get install -y unixodbc unixodbc-dev;

echo "Starting the Gunicorn server..."
exec gunicorn -w 2 -b 0.0.0.0:8080 app:app --timeout 120 --log-level=debug
