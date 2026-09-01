param(
    [switch]$SkipUpdate,
    [switch]$SkipTests,
    [switch]$RefreshDependencies
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $projectRoot
$backendDir = Join-Path $projectRoot "apps\pc-studio\backend"
$frontendDir = Join-Path $projectRoot "apps\pc-studio\frontend"
$python = Join-Path $backendDir ".venv\Scripts\python.exe"
$versionFile = Join-Path $projectRoot "VERSION"

function Run-Step {
    param([string]$Name, [scriptblock]$Action)

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
        throw "This helper updates origin/main and must run from local main. Current branch: $branch"
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
        throw "Commit or restore tracked edits before using the updater. Untracked runtime data may remain."
    }
}

function Get-ListeningProcessIds {
    param([int]$Port)

    if (Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue) {
        return @(
            Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess |
                Where-Object { $_ -and $_ -gt 0 } |
                Sort-Object -Unique
        )
    }

    $ids = @()
    $pattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
    foreach ($line in (netstat -ano)) {
        if ($line -match $pattern) {
            $ids += [int]$Matches[1]
        }
    }
    return @($ids | Sort-Object -Unique)
}

function Get-ProcessRecord {
    param([int]$ProcessId)

    if (-not (Get-Command Get-CimInstance -ErrorAction SilentlyContinue)) {
        return $null
    }
    return Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
}

function Test-AiTLProcessRecord {
    param([object]$ProcessRecord, [int]$Port)

    if (-not $ProcessRecord) {
        return $false
    }

    $combined = "$($ProcessRecord.ExecutablePath) $($ProcessRecord.CommandLine)".ToLowerInvariant()
    if ($Port -eq 8000) {
        return $combined.Contains($backendDir.ToLowerInvariant()) -and (
            $combined.Contains("uvicorn") -or
            $combined.Contains("app.main:app") -or
            $combined.Contains("powershell") -or
            $combined.Contains("pwsh")
        )
    }
    if ($Port -eq 5173) {
        return $combined.Contains($frontendDir.ToLowerInvariant()) -and (
            $combined.Contains("vite") -or
            $combined.Contains("npm") -or
            $combined.Contains("node") -or
            $combined.Contains("powershell") -or
            $combined.Contains("pwsh")
        )
    }
    return $false
}

function Get-AiTLProcessTreeRoot {
    param([int]$ProcessId, [int]$Port)

    $current = Get-ProcessRecord -ProcessId $ProcessId
    if (-not (Test-AiTLProcessRecord -ProcessRecord $current -Port $Port)) {
        return $null
    }

    $root = $current
    $visited = @{}
    while ($current -and $current.ParentProcessId -gt 0) {
        if ($visited.ContainsKey([string]$current.ProcessId)) {
            break
        }
        $visited[[string]$current.ProcessId] = $true

        $parent = Get-ProcessRecord -ProcessId ([int]$current.ParentProcessId)
        if (-not (Test-AiTLProcessRecord -ProcessRecord $parent -Port $Port)) {
            break
        }
        $root = $parent
        $current = $parent
    }
    return $root
}

function Wait-LocalPortFree {
    param([int]$Port, [int]$TimeoutSeconds = 10)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ((Get-ListeningProcessIds -Port $Port).Count -eq 0) {
            return
        }
        Start-Sleep -Milliseconds 200
    }
    throw "Timed out waiting for port $Port to become free."
}

function Stop-AiTLPortOwner {
    param([int]$Port, [string]$Role)

    $listeners = @(Get-ListeningProcessIds -Port $Port)
    if ($listeners.Count -eq 0) {
        return
    }
    if (-not (Get-Command Get-CimInstance -ErrorAction SilentlyContinue)) {
        throw "Port $Port is in use and its owner cannot be inspected safely. Stop it manually and rerun."
    }

    $roots = @{}
    foreach ($listenerPid in $listeners) {
        $record = Get-ProcessRecord -ProcessId ([int]$listenerPid)
        if (-not (Test-AiTLProcessRecord -ProcessRecord $record -Port $Port)) {
            $description = if ($record) { "$($record.Name) PID $listenerPid" } else { "PID $listenerPid" }
            throw "Port $Port is owned by $description, which is not identifiable as this AiTL $Role. It will not be terminated automatically."
        }

        $root = Get-AiTLProcessTreeRoot -ProcessId ([int]$listenerPid) -Port $Port
        if (-not $root) {
            throw "Could not identify the AiTL $Role process tree using port $Port."
        }
        $roots[[string]$root.ProcessId] = $root
    }

    foreach ($root in $roots.Values) {
        Write-Host "Stopping existing AiTL $Role process tree (PID $($root.ProcessId)) on port $Port..." -ForegroundColor DarkCyan
        & taskkill /PID $root.ProcessId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to stop existing AiTL $Role process tree PID $($root.ProcessId)."
        }
    }
    Wait-LocalPortFree -Port $Port
}

function Wait-HttpReady {
    param([string]$Url, [int]$TimeoutSeconds = 30)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                return
            }
        }
        catch {
            # Process may still be starting.
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for $Url"
}

Write-Host "AiTL update / test / run" -ForegroundColor Green
Write-Host "Repository: $repoRoot"
Write-Host "Project:    $projectRoot"

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found: $python`nRun scripts\setup_backend_windows.ps1 once, then retry."
}

# A reloaded runner must never enter the update branch again. This guard turns
# any future parameter-binding regression into one clear failure instead of an
# unbounded pull/reload loop.
if ($env:AITL_RUNNER_RELOADED -eq "1" -and -not $SkipUpdate) {
    throw "Runner reload guard triggered: -SkipUpdate was not bound. Recursive update prevented."
}

if (-not $SkipUpdate) {
    Push-Location $repoRoot
    try {
        Assert-MainBranch
        Assert-NoTrackedChanges
        Run-Step "Git status before update" { git status --short }

        $beforeHead = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $beforeHead) {
            throw "Unable to resolve the current Git commit before update."
        }

        Run-Step "Update from origin/main" { git pull --ff-only origin main }

        $afterHead = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $afterHead) {
            throw "Unable to resolve the current Git commit after update."
        }

        $changedPaths = if ($beforeHead -eq $afterHead) {
            @()
        }
        else {
            @(& git diff --name-only "$beforeHead..$afterHead")
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to determine files changed by the update."
        }

        $env:AITL_BACKEND_DEPS_CHANGED = if (@(
            $changedPaths | Where-Object {
                $_ -match '^AI_Traffic_Light/apps/pc-studio/backend/requirements(?:-training)?\.txt$'
            }
        ).Count -gt 0) { "1" } else { "0" }

        $env:AITL_FRONTEND_DEPS_CHANGED = if (@(
            $changedPaths | Where-Object {
                $_ -match '^AI_Traffic_Light/apps/pc-studio/frontend/(?:package\.json|package-lock\.json)$'
            }
        ).Count -gt 0) { "1" } else { "0" }
    }
    finally {
        Pop-Location
    }

    Write-Host "`nReloading the updated runner from the pulled code..." -ForegroundColor Cyan
    $env:AITL_RUNNER_RELOADED = "1"
    try {
        & $PSCommandPath -SkipUpdate -SkipTests:$SkipTests -RefreshDependencies:$RefreshDependencies
    }
    finally {
        Remove-Item Env:AITL_RUNNER_RELOADED -ErrorAction SilentlyContinue
    }
    return
}

Remove-Item Env:AITL_RUNNER_RELOADED -ErrorAction SilentlyContinue
$backendDependencyHint = $env:AITL_BACKEND_DEPS_CHANGED
$frontendDependencyHint = $env:AITL_FRONTEND_DEPS_CHANGED
Remove-Item Env:AITL_BACKEND_DEPS_CHANGED -ErrorAction SilentlyContinue
Remove-Item Env:AITL_FRONTEND_DEPS_CHANGED -ErrorAction SilentlyContinue

$backendDependenciesNeedRefresh = $RefreshDependencies -or $backendDependencyHint -ne "0"
$frontendDependenciesNeedRefresh = $RefreshDependencies -or $frontendDependencyHint -ne "0" -or -not (Test-Path (Join-Path $frontendDir "node_modules"))

if (Test-Path $versionFile) {
    Write-Host "`n=== Current project version ===" -ForegroundColor Cyan
    Get-Content $versionFile
}

$preflightTests = @("test_update_test_run_script.py")

if (-not $SkipTests) {
    Push-Location $projectRoot
    try {
        Run-Step "Python compile" { & $python -m compileall ".\apps\pc-studio\backend\app" ".\scripts" }
        Run-Step "Project structure and release consistency" { & $python ".\scripts\check_structure.py" }
        Run-Step "Update/test/run runner regression" { & $python ".\scripts\test_update_test_run_script.py" }
    }
    finally {
        Pop-Location
    }
}

if ($backendDependenciesNeedRefresh) {
    Push-Location $projectRoot
    try {
        Run-Step "Backend dependencies" { & $python -m pip install -r ".\apps\pc-studio\backend\requirements.txt" }
        if (Test-Path ".\apps\pc-studio\backend\requirements-training.txt") {
            Run-Step "Backend training dependencies" { & $python -m pip install -r ".\apps\pc-studio\backend\requirements-training.txt" }
        }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "`n=== Backend dependencies ===" -ForegroundColor DarkCyan
    Write-Host "Skipped: dependency manifests did not change. Use -RefreshDependencies to force refresh."
}

if (-not $SkipTests) {
    Push-Location $projectRoot
    try {
        $manualHardwareTests = @(
            "test_camera_transport_benchmark.py",
            "test_camera_transport_isolation.py"
        )

        $tests = Get-ChildItem ".\scripts\test_*.py" |
            Where-Object {
                $_.Name -ne "test_backend_smoke.py" -and
                $_.Name -notin $manualHardwareTests -and
                $_.Name -notin $preflightTests
            } |
            Sort-Object Name

        foreach ($test in $tests) {
            Run-Step "Backend regression: $($test.Name)" { & $python $test.FullName }
        }

        foreach ($manualTest in $manualHardwareTests) {
            if (Test-Path (Join-Path ".\scripts" $manualTest)) {
                Write-Host "`n=== Hardware camera test excluded: $manualTest ===" -ForegroundColor DarkCyan
                Write-Host "Run manually with --host after flashing matching diagnostic firmware."
            }
        }
    }
    finally {
        Pop-Location
    }
}

if ($frontendDependenciesNeedRefresh) {
    Push-Location $frontendDir
    try {
        Run-Step "Frontend dependencies" { npm ci }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "`n=== Frontend dependencies ===" -ForegroundColor DarkCyan
    Write-Host "Skipped: package manifests did not change and node_modules exists. Use -RefreshDependencies to force refresh."
}

if (-not $SkipTests) {
    Push-Location $frontendDir
    try {
        Run-Step "Frontend typecheck" { npm run typecheck }
        Run-Step "Frontend production build" { npm run build }
    }
    finally {
        Pop-Location
    }

    Push-Location $repoRoot
    try {
        Run-Step "Git whitespace check" { git diff --check }
        Assert-NoTrackedChanges
    }
    finally {
        Pop-Location
    }
}

Stop-AiTLPortOwner -Port 5173 -Role "frontend"
Stop-AiTLPortOwner -Port 8000 -Role "backend"

Write-Host "`nAll requested non-live checks passed. Starting PC Studio..." -ForegroundColor Green
$shellExe = (Get-Process -Id $PID).Path
$backendCommand = "Set-Location '$backendDir'; & '$python' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
$frontendCommand = "Set-Location '$frontendDir'; npm run dev -- --port 5173 --strictPort"

Start-Process -FilePath $shellExe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand | Out-Null
Wait-HttpReady "http://127.0.0.1:8000/health"

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
Wait-HttpReady "http://127.0.0.1:5173/"

Write-Host "`nPC Studio is running." -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:5173/"
Start-Process "http://localhost:5173/"
