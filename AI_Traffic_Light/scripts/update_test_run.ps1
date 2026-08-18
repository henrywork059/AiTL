param(
    [switch]$SkipUpdate,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $projectRoot
$backendDir = Join-Path $projectRoot "apps\pc-studio\backend"
$frontendDir = Join-Path $projectRoot "apps\pc-studio\frontend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$versionFile = Join-Path $projectRoot "VERSION"

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

function Assert-MainBranch {
    $branch = (& git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the current Git branch."
    }
    if ($branch -ne "main") {
        throw "This helper updates origin/main and must be run from the local main branch. Current branch: $branch"
    }
}

function Assert-NoTrackedChanges {
    & git diff --quiet --ignore-submodules --
    $worktreeCode = $LASTEXITCODE
    & git diff --cached --quiet --ignore-submodules --
    $indexCode = $LASTEXITCODE

    if ($worktreeCode -gt 1 -or $indexCode -gt 1) {
        throw "Git could not inspect the tracked working tree safely."
    }
    if ($worktreeCode -eq 1 -or $indexCode -eq 1) {
        Write-Host "Tracked local changes detected:" -ForegroundColor Yellow
        & git status --short
        throw "Commit, restore, or deliberately preserve the tracked edits before using the automatic updater. Untracked runtime data does not need to be removed."
    }
}

function Test-LocalPortInUse {
    param([int]$Port)

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    }

    $match = netstat -ano | Select-String -Pattern ":$Port\s+.*LISTENING"
    return [bool]$match
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                return
            }
        }
        catch {
            # The process may still be starting. Retry until the deadline.
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for $Url"
}

Write-Host "AiTL update / test / run" -ForegroundColor Green
Write-Host "Repository: $repoRoot"
Write-Host "Project:    $projectRoot"

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found: $python`nCreate/install the backend .venv first."
}

if (-not $SkipUpdate) {
    Push-Location $repoRoot
    try {
        Assert-MainBranch
        Assert-NoTrackedChanges
        Run-Step "Git status before update" { git status --short }
        Run-Step "Update from origin/main" { git pull --ff-only origin main }
    }
    finally {
        Pop-Location
    }

    # The pull may have replaced this helper. Re-enter it from disk so the
    # newly pulled version owns all dependency, test, and startup behavior.
    Write-Host "`nReloading the updated runner from the pulled code..." -ForegroundColor Cyan
    if ($SkipTests) {
        & $PSCommandPath -SkipUpdate -SkipTests
    }
    else {
        & $PSCommandPath -SkipUpdate
    }
    return
}

if (Test-Path $versionFile) {
    Write-Host "`n=== Current project version ===" -ForegroundColor Cyan
    Get-Content $versionFile
}

if (-not $SkipTests) {
    Push-Location $projectRoot
    try {
        Run-Step "Backend dependencies" { & $python -m pip install -r ".\apps\pc-studio\backend\requirements.txt" }
        if (Test-Path ".\apps\pc-studio\backend\requirements-training.txt") {
            Run-Step "Backend training dependencies" { & $python -m pip install -r ".\apps\pc-studio\backend\requirements-training.txt" }
        }
        Run-Step "Python compile" { & $python -m compileall ".\apps\pc-studio\backend\app" ".\scripts" }
        Run-Step "Project structure" { & $python ".\scripts\check_structure.py" }

        $tests = Get-ChildItem ".\scripts\test_*.py" |
            Where-Object { $_.Name -ne "test_backend_smoke.py" } |
            Sort-Object Name

        foreach ($test in $tests) {
            Run-Step "Backend regression: $($test.Name)" { & $python $test.FullName }
        }
    }
    finally {
        Pop-Location
    }

    Push-Location $frontendDir
    try {
        Run-Step "Frontend dependencies" { npm ci }
        Run-Step "Frontend typecheck" { npm run typecheck }
        Run-Step "Frontend production build" { npm run build }
    }
    finally {
        Pop-Location
    }

    Push-Location $repoRoot
    try {
        Run-Step "Git whitespace check" { git diff --check }
    }
    finally {
        Pop-Location
    }
}
elif (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Push-Location $frontendDir
    try {
        Run-Step "Frontend dependencies" { npm ci }
    }
    finally {
        Pop-Location
    }
}

if (Test-LocalPortInUse 8000) {
    throw "Port 8000 is already in use. Stop the existing backend/process before running this helper."
}
if (Test-LocalPortInUse 5173) {
    throw "Port 5173 is already in use. Stop the existing frontend/process before running this helper."
}

Write-Host "`nAll requested non-live checks passed. Starting PC Studio..." -ForegroundColor Green

$shellExe = (Get-Process -Id $PID).Path
$backendCommand = "Set-Location '$backendDir'; & '$python' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
$frontendCommand = "Set-Location '$frontendDir'; npm run dev -- --port 5173 --strictPort"

Start-Process -FilePath $shellExe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand | Out-Null
Wait-HttpReady "http://127.0.0.1:8000/health" 30

if (-not $SkipTests) {
    Push-Location $projectRoot
    try {
        Run-Step "Live backend smoke" { & $python ".\scripts\test_backend_smoke.py" }
    }
    finally {
        Pop-Location
    }
}

Start-Process -FilePath $shellExe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand | Out-Null
Wait-HttpReady "http://127.0.0.1:5173/" 30

Write-Host "`nPC Studio is running." -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:5173/"
Start-Process "http://localhost:5173/"
