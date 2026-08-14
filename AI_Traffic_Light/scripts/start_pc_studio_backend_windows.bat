@echo off
setlocal
cd /d "%~dp0\..\apps\pc-studio\backend"
if not exist .venv (
  echo Creating backend virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
