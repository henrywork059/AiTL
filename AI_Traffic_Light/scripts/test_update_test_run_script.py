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
    assert "$PSCommandPath -SkipUpdate" in text
    assert "pip install -r" in text
    assert 'Run-Step "Frontend dependencies" { npm ci }' in text
    assert "Get-NetTCPConnection" in text or "netstat -ano" in text
    assert "Wait-HttpReady" in text
    assert "test_backend_smoke.py" in text
    assert "--strictPort" in text
    assert "Start-Sleep -Seconds 2" not in text
    assert not re.search(r"(?m)^\s*elif\s*\(", text), "PowerShell runner must use elseif, not elif"
    assert re.search(r"(?m)^\s*elseif\s*\(", text), "PowerShell runner should retain the SkipTests dependency branch"

    # New zero-argument offline regressions should join the normal workflow by
    # naming convention rather than requiring a manually maintained test list.
    assert 'Get-ChildItem ".\\scripts\\test_*.py"' in text
    assert '$_ .Name' not in text  # reject an easy-to-miss malformed PowerShell property access
    assert 'test_backend_smoke.py' in text
    assert '$manualHardwareTests' in text
    assert 'Sort-Object Name' in text
    assert 'Run-Step "Backend regression: $($test.Name)"' in text

    # The runner must never mutate tracked release metadata. V036's historical
    # finalizer caused CHANGELOG/projectVersion edits that blocked the next pull.
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

    # The obsolete behavior should not return: known AiTL listeners are now
    # restarted automatically, while unrelated listeners remain protected.
    assert "Stop the existing backend/process before running this helper" not in text
    assert "Stop the existing frontend/process before running this helper" not in text

    print("[PASS] update/test/run helper protects tracked work and only fast-forwards main")
    print("[PASS] runner auto-discovers zero-argument test_*.py regressions in deterministic name order")
    print("[PASS] hardware-only camera CLIs remain explicitly excluded from the automatic regression sweep")
    print("[PASS] runner no longer invokes any candidate metadata finalizer")
    print("[PASS] runner remains read-only for tracked release/source files")
    print("[PASS] post-test tracked-cleanliness guard prevents self-dirtying regressions")
    print("[PASS] pulled runner reloads itself before testing the newly updated code")
    print("[PASS] dependency refresh, automatic live smoke, readiness waits, and strict ports are enforced")
    print("[PASS] existing AiTL backend/frontend processes are safely replaced on repeated runs")
    print("[PASS] unrelated processes using PC Studio ports are never terminated automatically")
    print("[PASS] PowerShell control-flow syntax uses elseif and rejects Python-style elif")
    print("[PASS] helper never uses destructive git clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
