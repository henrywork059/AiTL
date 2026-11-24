$ErrorActionPreference = "Stop"
Push-Location "$PSScriptRoot\..\apps\pc-studio\backend"
try {
    $python = ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        if (Test-Path ".venv") {
            throw "Incomplete backend .venv; repair or move it before retrying setup."
        }
        if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
            throw "Install Python 3.11 with the Windows Python launcher (py), then retry."
        }
        & py -3.11 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Python 3.11 virtual environment creation failed." }
    }
    & $python --version
    if ($LASTEXITCODE -ne 0) { throw "Existing backend Python could not start." }
    & $python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
    Write-Host "Backend environment ready. Use scripts\update_test_run.ps1 for full validation."
}
finally {
    Pop-Location
}
