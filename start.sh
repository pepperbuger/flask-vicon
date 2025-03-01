#!/bin/bash
echo "Installing ODBC dependencies..."
apt-get update && apt-get install -y unixodbc unixodbc-dev

echo "Starting the application..."
python app.py
