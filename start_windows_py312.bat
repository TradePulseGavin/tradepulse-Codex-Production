@echo off
setlocal
cd /d %~dp0

echo Trading Copilot starting with Python 3.12...
echo.

py -3.12 --version >nul 2>nul
if %errorlevel% neq 0 (
  echo Python 3.12 was not found.
  echo Install Python 3.12, then run this file again.
  pause
  exit /b 1
)

if exist .venv (
  echo Removing old virtual environment...
  rmdir /s /q .venv
)

echo Creating virtual environment with Python 3.12...
py -3.12 -m venv .venv
call .venv\Scripts\activate.bat

echo Upgrading pip/wheel...
python -m pip install --upgrade pip setuptools wheel

echo Installing Trading Copilot requirements...
python -m pip install --prefer-binary -r requirements.txt
if %errorlevel% neq 0 (
  echo Install failed.
  pause
  exit /b 1
)

echo Starting dashboard at http://127.0.0.1:8000
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
