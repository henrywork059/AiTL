@echo off
setlocal
cd /d "%~dp0\.."
python scripts\test_backend_smoke.py
pause
