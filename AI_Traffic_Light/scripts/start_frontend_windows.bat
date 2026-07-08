@echo off
cd /d %~dp0\..\apps\pc-studio\frontend
if not exist node_modules (
  npm install
)
npm run dev
