@echo off
title ClinicOS - Clinic Management System
color 0A

echo.
echo  ================================
echo       ClinicOS - Starting...
echo  ================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python is not installed!
    echo.
    echo  Please install Python from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

:: Install Flask if not already installed
echo  Checking dependencies...
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing Flask (one time only)...
    pip install flask
)

echo.
echo  ✓ Starting ClinicOS...
echo.
echo  Open your browser and go to:
echo  ► http://localhost:5000
echo.
echo  To access from your phone (same WiFi):
echo  ► Find your PC IP address and use http://YOUR-IP:5000
echo.
echo  Default login: admin / admin123
echo  (Change this password after first login!)
echo.
echo  Press Ctrl+C to stop the server.
echo  ================================
echo.

:: Get and display local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%
echo  Your PC IP address: %IP%
echo  Phone access URL: http://%IP%:5000
echo.

:: Start the app and open browser
start "" "http://localhost:5000"
python app.py

pause
