# Patch 0_5_49 — Reproducible offline regression execution

Candidate `0_5_49`, previous `0_5_48`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap Update 05 / H04.

## Root cause and change

Use one Python offline regression runner in Windows and CI, with deterministic discovery, shared live/hardware exclusions and fail-fast subprocess exit handling. Focused changes to camera/inference/model or camera firmware conservatively run the full suite; missing/deleted tests or empty regression families also fall back to all. Fresh Windows setup targets Python 3.11 and checks native exit codes without replacing an existing venv.

From `AI_Traffic_Light/` using a Python environment with backend requirements installed:

```text
python scripts/run_offline_tests.py --list
python scripts/run_offline_tests.py
```

Use `python scripts/run_offline_tests.py --focused test_v0548_observation_invalidation.py` for a specific offline regression. On Windows, use the backend venv interpreter if it is not active.

Core direct backend dependencies remain pinned; npm uses the existing lockfile. Optional training dependencies and transitive Python dependencies are not fully locked; no unverified version changes are introduced. This does not establish complete environment reproducibility or resolve network/DNS failure.

## Evidence

Executed original camera filename selection expression with five fixture names: only 1/5 selected, four numbered lifecycle regressions omitted. Executed patched test_offline_test_discovery.py and test_select_changed_tests.py on local Python 3.13.5: both passed, including actual child process execution/fail-fast exit 7; compileall of the four Python files passed. FNV-1a source checks: runner 8d76d515, runner test 351b1672, selector bd6c3d59, selector test 2fb1332b. Direct GitHub ls-remote failed DNS resolution; PowerShell not installed locally. Full repository checkout, Windows runner, CI and hardware acceptance remain pending.

No application behavior, firmware, signal policy or public-road actuation changes. Next: Update 06 / A01, stale-input virtual signal fallback, subject to earlier validation blockers.
