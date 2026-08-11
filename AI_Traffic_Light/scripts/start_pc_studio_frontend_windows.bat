@echo off
setlocal
cd /d "%~dp0\..\apps\pc-studio\frontend"
if not exist node_modules (
  echo Installing frontend packages...
  npm install
)
npm run dev
