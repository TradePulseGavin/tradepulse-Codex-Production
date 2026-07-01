@echo off
setlocal
cd /d %~dp0

echo Trading Copilot starting...
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  set PY_CMD=py
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set PY_CMD=python
  ) else (
    echo Python was not found.
    echo Install Python from python.org or Python Install Manager, then run this again.
    pause
    exit /b 1
  )
)

echo Using Python:
%PY_CMD% --version

echo.
echo Creating virtual environment if needed...
if not exist .venv (
  %PY_CMD% -m venv .venv
)

call .venv\Scripts\activate.bat

echo.
echo Upgrading pip/wheel...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Installing Trading Copilot requirements...
python -m pip install --prefer-binary -r requirements.txt
if %errorlevel% neq 0 (
  echo.
  echo Install failed. If this mentions pandas, install Python 3.12 and delete the .venv folder, then run start_windows again.
  pause
  exit /b 1
)

echo.
echo Starting dashboard at http://127.0.0.1:8000
echo Keep this window open while using Trading Copilot.
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
