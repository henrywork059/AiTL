from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "update_test_run.ps1"
FINALIZER = ROOT / "scripts" / "apply_v036_full_patch.ps1"

text = RUNNER.read_text(encoding="utf-8")
assert FINALIZER.is_file(), "V036 metadata finalizer is missing"
assert "function Invoke-CandidateMetadataFinalizer" in text
assert 'if ($currentVersion -ne "0_3_6")' in text
assert "Invoke-CandidateMetadataFinalizer" in text
assert 'Run-Step "Project structure"' in text
assert text.rfind("Invoke-CandidateMetadataFinalizer") < text.index('Run-Step "Project structure"'), (
    "V036 metadata finalization must occur before structure validation"
)
print("V036 metadata runner regression passed")
