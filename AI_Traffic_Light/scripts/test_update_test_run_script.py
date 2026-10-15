from pathlib import Path
import os
import re
import subprocess
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "update_test_run.ps1"


def test_windows_uvicorn_ancestry(text: str) -> None:
    """Execute the real runner predicates against mocked Windows process records."""
    if os.name != "nt":
        return

    # The runner does not start the application until after this marker.
    definitions, marker, _ = text.partition('Write-Host "AiTL update / test / run"')
    assert marker
    fixture = r"""
$python = 'C:\AiTL\backend\.venv\Scripts\python.exe'
$global:records = @{}
$launcher = [pscustomobject]@{
    ProcessId = 35220; ParentProcessId = 14756
    ExecutablePath = $python
    CommandLine = 'C:\AiTL\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
}
$worker = [pscustomobject]@{
    ProcessId = 35864; ParentProcessId = 35220
    ExecutablePath = 'C:\Python310\python.exe'
    CommandLine = 'C:\Python310\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000'
}
$global:records['35220'] = $launcher
$global:records['35864'] = $worker
$global:records['14756'] = [pscustomobject]@{
    ProcessId = 14756; ParentProcessId = 0
    ExecutablePath = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
    CommandLine = 'powershell.exe -NoExit'
}
function Get-ProcessRecord {
    param([int]$ProcessId)
    return $global:records[[string]$ProcessId]
}
if (-not (Test-AiTLProcessRecord -ProcessRecord $launcher -Port 8000)) {
    throw 'AiTL venv launcher was rejected.'
}
if (-not (Test-AiTLProcessRecord -ProcessRecord $worker -Port 8000)) {
    throw 'Verified system-python child was rejected.'
}
$root = Get-AiTLProcessTreeRoot -ProcessId 35864 -Port 8000
if (-not $root -or $root.ProcessId -ne 35220) {
    throw 'Process tree did not stop at the virtualenv launcher.'
}
$spawn = [pscustomobject]@{
    ProcessId = 35865; ParentProcessId = 35220
    ExecutablePath = 'C:\Python310\python.exe'
    CommandLine = 'C:\Python310\python.exe -c spawn_main(parent_pid=35220) --multiprocessing-fork'
}
if (-not (Test-AiTLProcessRecord -ProcessRecord $spawn -Port 8000)) {
    throw 'Verified multiprocessing child was rejected.'
}
$unrelated = [pscustomobject]@{
    ProcessId = 9999; ParentProcessId = 0
    ExecutablePath = 'C:\Python310\python.exe'
    CommandLine = $worker.CommandLine
}
if (Test-AiTLProcessRecord -ProcessRecord $unrelated -Port 8000) {
    throw 'Unrelated Python port owner was accepted.'
}
$otherService = [pscustomobject]@{
    ProcessId = 10001; ParentProcessId = 35220
    ExecutablePath = 'C:\Python310\python.exe'
    CommandLine = 'C:\Python310\python.exe -m http.server 8000'
}
if (Test-AiTLProcessRecord -ProcessRecord $otherService -Port 8000) {
    throw 'Unrelated module was accepted.'
}
$global:records['111'] = [pscustomobject]@{
    ProcessId = 111; ParentProcessId = 0
    ExecutablePath = 'C:\Python310\python.exe'
    CommandLine = $launcher.CommandLine
}
$wrongParent = [pscustomobject]@{
    ProcessId = 112; ParentProcessId = 111
    ExecutablePath = 'C:\Python310\python.exe'
    CommandLine = $worker.CommandLine
}
if (Test-AiTLProcessRecord -ProcessRecord $wrongParent -Port 8000) {
    throw 'Non-AiTL parent was accepted.'
}
Write-Host '[PASS] verified Windows Uvicorn child and unrelated-process rejection'
"""
    with TemporaryDirectory() as directory:
        test_file = Path(directory) / "test_aitl_process_identity.ps1"
        test_file.write_text(definitions + fixture, encoding="utf-8")
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(test_file)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)


def main() -> int:
    text = SCRIPT.read_text(encoding="utf-8")

    # Update safety and tracked-data preservation.
    assert "git clean" not in text.lower()
    assert "git pull --ff-only origin main" in text
    assert "Assert-MainBranch" in text
    assert "git diff --quiet" in text
    assert "git diff --cached --quiet" in text
    assert "git rev-parse HEAD" in text
    assert "git diff --name-only" in text

    # The pulled runner is re-entered exactly once. Explicit switch binding plus
    # an environment guard prevents the recursive pull/reload loop seen on V0312.
    assert '$env:AITL_RUNNER_RELOADED = "1"' in text
    assert 'if ($env:AITL_RUNNER_RELOADED -eq "1" -and -not $SkipUpdate)' in text
    assert "Recursive update prevented" in text
    assert '& $PSCommandPath -SkipUpdate -SkipTests:$SkipTests -ChangedTests:$ChangedTests -RefreshDependencies:$RefreshDependencies' in text
    assert '$reloadArgs = @("-SkipUpdate")' not in text
    assert "Remove-Item Env:AITL_RUNNER_RELOADED" in text

    # Focused startup selection, forwarding and safe fallback remain wired.
    assert '[switch]$ChangedTests' in text
    assert 'AITL_CHANGED_PATHS' in text
    assert 'git show --pretty=format: --name-only HEAD' in text
    assert 'select_changed_tests.py' in text
    assert '$runAllRegressions' in text
    assert '$runFrontendChecks' in text
    assert '$_.Name -in $selectedTests' in text
    assert 'Run-Step "Changed Python compile"' in text
    assert 'Run-Step "Live backend smoke"' in text

    # Dependency refresh remains update-aware with an explicit recovery override.
    assert '[switch]$RefreshDependencies' in text
    assert "AITL_BACKEND_DEPS_CHANGED" in text
    assert "AITL_FRONTEND_DEPS_CHANGED" in text
    assert "requirements(?:-training)?\\.txt" in text
    assert "package-lock\\.json" in text and "package\\.json" in text
    assert "pip install -r" in text
    assert 'Run-Step "Frontend dependencies" { npm ci }' in text
    assert "Use -RefreshDependencies" in text

    # Cheap guards run before dependency installation. check_structure.py is the
    # single release/structure authority; the old duplicate release script must
    # not be executed or listed as a preflight test.
    for marker in (
        'Run-Step "Python compile"',
        'Run-Step "Project structure and release consistency"',
        'Run-Step "Update/test/run runner regression"',
    ):
        assert marker in text
    assert "test_release_documentation_consistency.py" not in text
    dependency_step = text.index('Run-Step "Backend dependencies"')
    assert text.index('Run-Step "Project structure and release consistency"') < dependency_step
    assert text.index('Run-Step "Update/test/run runner regression"') < dependency_step

    # Automatic regressions and hardware-only exclusions remain deterministic.
    assert 'Get-ChildItem ".\\scripts\\test_*.py"' in text
    assert '$manualHardwareTests' in text
    assert '$preflightTests' in text
    assert '$preflightTests = @("test_update_test_run_script.py")' in text
    assert 'Sort-Object Name' in text
    assert 'Run-Step "Backend regression: $($test.Name)"' in text
    assert '$_.Name -notin $preflightTests' in text

    # Existing AiTL processes may be replaced, but unrelated port owners are protected.
    assert "Get-CimInstance Win32_Process" in text
    assert "Get-AiTLProcessTreeRoot" in text
    assert "taskkill /PID" in text and "/T /F" in text
    # A Windows virtualenv may delegate to system python.exe. Only its direct
    # child is accepted, and only if the parent's venv and uvicorn arguments
    # match the expected project. Unknown port owners must still be rejected.
    assert '$command.Contains("spawn_main")' in text
    assert '$command.Contains("--multiprocessing-fork")' in text
    assert '$backendLaunch -or $spawnWorker' in text
    assert '$executable.EndsWith("\\python.exe")' in text
    assert 'Get-ProcessRecord -ProcessId ([int]$ProcessRecord.ParentProcessId)' in text
    assert '$parentCommand.Contains("app.main:app")' in text
    assert '$parentCommand.Contains("--reload")' in text
    assert '$parentCommand.Contains("--port 8000")' in text
    assert '"$($parent.ExecutablePath)".ToLowerInvariant() -eq $python.ToLowerInvariant()' in text
    assert 'if ($Port -eq 8000 -and "$($parent.ExecutablePath)".ToLowerInvariant() -ne $python.ToLowerInvariant())' in text
    assert 'Stop-AiTLPortOwner -Port 5173 -Role "frontend"' in text
    assert 'Stop-AiTLPortOwner -Port 8000 -Role "backend"' in text
    assert "which is not identifiable as this AiTL" in text
    assert "It will not be terminated automatically" in text
    assert text.index('Stop-AiTLPortOwner -Port 8000 -Role "backend"') < text.index("Start-Process -FilePath $shellExe")

    # Startup and live validation remain automatic.
    assert "Wait-HttpReady" in text
    assert "test_backend_smoke.py" in text
    assert "--strictPort" in text
    assert "Start-Sleep -Seconds 2" not in text
    assert not re.search(r"(?m)^\s*elif\s*\(", text)

    # Runner stays read-only for tracked release/source files.
    assert "Invoke-CandidateMetadataFinalizer" not in text
    assert "apply_v036_full_patch.ps1" not in text
    assert "Set-Content" not in text
    assert "Add-Content" not in text
    assert text.count("Assert-NoTrackedChanges") >= 3

    print("[PASS] updater fast-forwards main without deleting runtime data")
    print("[PASS] pulled runner reloads exactly once and recursive update is guarded")
    print("[PASS] dependency refresh remains change-aware with force-refresh recovery")
    print("[PASS] structure/release validation has one preflight authority before dependency work")
    print("[PASS] automatic regressions, typecheck/build and live smoke remain wired")
    test_windows_uvicorn_ancestry(text)
    print("[PASS] existing AiTL processes are replaced while unrelated port owners stay protected")
    print("[PASS] runner remains read-only for tracked release/source files")
    print("[PASS] change-scoped startup mode retains safe fallback and live smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
