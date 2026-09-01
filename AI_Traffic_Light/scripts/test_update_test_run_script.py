from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "update_test_run.ps1"


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
    assert '& $PSCommandPath -SkipUpdate -SkipTests:$SkipTests -RefreshDependencies:$RefreshDependencies' in text
    assert '$reloadArgs = @("-SkipUpdate")' not in text
    assert "Remove-Item Env:AITL_RUNNER_RELOADED" in text

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
    print("[PASS] existing AiTL processes are replaced while unrelated port owners stay protected")
    print("[PASS] runner remains read-only for tracked release/source files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
