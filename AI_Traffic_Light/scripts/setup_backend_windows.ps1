Set-Location "$PSScriptRoot\..\apps\pc-studio\backend"
if (!(Test-Path ".venv")) {
  python -m venv .venv
}
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Write-Host "Backend environment ready. Run: uvicorn app.main:app --reload"
