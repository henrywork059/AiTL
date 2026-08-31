from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "update_test_run.ps1"


def main() -> int:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "git clean" not in text.lower()
    assert "git pull --ff-only origin main" in text
    assert "Assert-MainBranch" in text
    assert "git diff --quiet" in text
    assert "git diff --cached --quiet" in text
    assert "git rev-parse HEAD" in text
    assert "git diff --name-only" in text
    assert '[switch]$RefreshDependencies' in text
    assert '$reloadArgs = @("-SkipUpdate")' in text
    assert '& $PSCommandPath @reloadArgs' in text
    assert "pip install -r" in text
    assert 'Run-Step "Frontend dependencies" { npm ci }' in text
    assert "Get-NetTCPConnection" in text or "netstat -ano" in text
    assert "Wait-HttpReady" in text
    assert "test_backend_smoke.py" in text
    assert "--strictPort" in text
    assert "Start-Sleep -Seconds 2" not in text
    assert not re.search(r"(?m)^\s*elif\s*\(", text), "PowerShell runner must never use Python-style elif"

    # Cheap repository/release checks must fail before dependency refresh. This
    # prevents metadata/structure mistakes from wasting time on pip/npm work.
    for marker in (
        'Run-Step "Python compile"',
        'Run-Step "Project structure"',
        'Run-Step "Release documentation consistency"',
        'Run-Step "Update/test/run runner regression"',
    ):
        assert marker in text
    backend_dependency_step = text.index('Run-Step "Backend dependencies"')
    assert text.index('Run-Step "Project structure"') < backend_dependency_step
    assert text.index('Run-Step "Release documentation consistency"') < backend_dependency_step
    assert text.index('Run-Step "Update/test/run runner regression"') < backend_dependency_step

    # Normal update runs refresh dependencies only when Git says their manifests
    # changed. Direct -SkipUpdate use is conservative; force refresh remains
    # available without changing the normal one-command workflow.
    assert "AITL_BACKEND_DEPS_CHANGED" in text
    assert "AITL_FRONTEND_DEPS_CHANGED" in text
    assert "requirements(?:-training)?\\.txt" in text
    assert "package-lock\\.json" in text and "package\\.json" in text
    assert '$backendDependenciesNeedRefresh = $RefreshDependencies -or $backendDependencyHint -ne "0"' in text
    assert '$frontendDependenciesNeedRefresh = $RefreshDependencies -or $frontendDependencyHint -ne "0"' in text
    assert "Remove-Item Env:AITL_BACKEND_DEPS_CHANGED" in text
    assert "Remove-Item Env:AITL_FRONTEND_DEPS_CHANGED" in text
    assert "dependency manifests did not change" in text
    assert "Use -RefreshDependencies" in text

    # New zero-argument offline regressions should join the normal workflow by
    # naming convention rather than requiring a manually maintained test list.
    assert 'Get-ChildItem ".\\scripts\\test_*.py"' in text
    assert '$_ .Name' not in text  # reject an easy-to-miss malformed PowerShell property access
    assert 'test_backend_smoke.py' in text
    assert '$manualHardwareTests' in text
    assert '$preflightTests' in text
    assert 'test_release_documentation_consistency.py' in text
    assert 'test_update_test_run_script.py' in text
    assert 'Sort-Object Name' in text
    assert 'Run-Step "Backend regression: $($test.Name)"' in text
    assert '$_.Name -notin $preflightTests' in text

    # The runner must never mutate tracked release metadata. Dependency hints are
    # process environment variables only and are consumed/cleared after reload.
    assert "Invoke-CandidateMetadataFinalizer" not in text
    assert "apply_v036_full_patch.ps1" not in text
    assert "WriteAllText" not in text
    assert "Set-Content" not in text
    assert "Add-Content" not in text

    # Re-check tracked cleanliness after the non-live tests so a future helper
    # regression is caught immediately instead of breaking the next update run.
    assert text.count("Assert-NoTrackedChanges") >= 3

    # Re-running the same command must safely replace an existing AiTL PC Studio
    # process tree instead of making the user manually free ports 8000/5173.
    assert "Stop-AiTLPortOwner" in text
    assert 'Stop-AiTLPortOwner -Port 5173 -Role "frontend"' in text
    assert 'Stop-AiTLPortOwner -Port 8000 -Role "backend"' in text
    assert "Get-CimInstance Win32_Process" in text
    assert "Get-AiTLProcessTreeRoot" in text
    assert "taskkill /PID" in text and "/T /F" in text
    assert "$backendMarker = $backendDir.ToLowerInvariant()" in text
    assert "$frontendMarker = $frontendDir.ToLowerInvariant()" in text
    assert "which is not identifiable as this AiTL" in text
    assert "It will not be terminated automatically" in text
    assert text.index('Stop-AiTLPortOwner -Port 8000 -Role "backend"') < text.index("Start-Process -FilePath $shellExe")

    assert "Stop the existing backend/process before running this helper" not in text
    assert "Stop the existing frontend/process before running this helper" not in text

    print("[PASS] update/test/run helper protects tracked work and only fast-forwards main")
    print("[PASS] cheap compile/structure/release/runner guards execute before dependency refresh")
    print("[PASS] unchanged dependency manifests skip repeated pip/npm installation on normal updates")
    print("[PASS] -RefreshDependencies provides an explicit recovery/force-refresh path")
    print("[PASS] runner auto-discovers zero-argument test_*.py regressions in deterministic name order")
    print("[PASS] preflight and hardware-only tests are excluded from duplicate/automatic misuse")
    print("[PASS] runner remains read-only for tracked release/source files")
    print("[PASS] post-test tracked-cleanliness guard prevents self-dirtying regressions")
    print("[PASS] pulled runner reloads itself before testing the newly updated code")
    print("[PASS] automatic live smoke, readiness waits, and strict ports are enforced")
    print("[PASS] existing AiTL backend/frontend processes are safely replaced on repeated runs")
    print("[PASS] unrelated processes using PC Studio ports are never terminated automatically")
    print("[PASS] PowerShell runner rejects Python-style elif")
    print("[PASS] helper never uses destructive git clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
