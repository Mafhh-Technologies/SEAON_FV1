@echo off
setlocal
title SEAON ERP
cd /d "%~dp0Backend"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating the Python environment...
    py -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/3] Installing/updating SEAON packages...
python -m pip install -r requirements.txt

echo [3/3] Starting SEAON ERP...
echo.
echo Open http://127.0.0.1:8000/app/login.html
echo Login: admin@seaon.com
echo Password: Admin@123
echo.
python app.py

pause
