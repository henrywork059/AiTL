from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "update_test_run.ps1"
FINALIZER = ROOT / "scripts" / "apply_v036_full_patch.ps1"

text = RUNNER.read_text(encoding="utf-8")

# The V036 finalizer is retained only as historical/manual-recovery tooling.
# The normal update/test/run helper must never invoke it because doing so
# rewrites tracked metadata and makes the next GitHub update fail on a dirty tree.
assert FINALIZER.is_file(), "Archived V036 metadata finalizer is missing"
assert "apply_v036_full_patch.ps1" not in text, (
    "Normal runner must not invoke the historical V036 metadata finalizer"
)
assert "function Invoke-CandidateMetadataFinalizer" not in text
assert "Invoke-CandidateMetadataFinalizer" not in text
assert 'if ($currentVersion -ne "0_3_6")' not in text
assert 'Run-Step "Project structure"' in text
assert "Assert-NoTrackedChanges" in text
assert "git diff --quiet" in text
assert "git diff --cached --quiet" in text

print("[PASS] historical V036 metadata finalizer remains available for manual recovery")
print("[PASS] normal update/test/run flow does not invoke or define the obsolete metadata finalizer")
print("[PASS] tracked-work protection remains enabled")
