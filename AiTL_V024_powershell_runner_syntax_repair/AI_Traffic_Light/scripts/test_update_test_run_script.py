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

    print("[PASS] update/test/run helper protects tracked work and only fast-forwards main")
    print("[PASS] pulled runner reloads itself before testing the newly updated code")
    print("[PASS] dependency refresh, automatic live smoke, readiness waits, and strict ports are enforced")
    print("[PASS] PowerShell control-flow syntax uses elseif and rejects Python-style elif")
    print("[PASS] helper never uses destructive git clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
