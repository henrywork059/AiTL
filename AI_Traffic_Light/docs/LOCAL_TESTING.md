# Local Testing — V0316

```text
version: 0_3_16
previous_version: 0_3_15
passed_baseline: 0_3_11
status: focused startup validation candidate
```

## Fast changed-tests startup

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Verify Git updates and runner reload exactly once. Check the printed changed-file count and the selected offline regressions. Verify that startup always completes the structure/release guard, runner regression, safe restart, backend readiness, live smoke and browser launch.
If there is no newly pulled commit, the latest commit determines test scope. Shared/unknown paths and manifest changes trigger full-suite fallback.

## Full validation

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Default mode still compiles backend scripts, validates structure/version, runs all automatic offline regressions (excluding manual hardware tests), typechecks/builds frontend, checks Git cleanliness, safely restarts services, executes live smoke and opens PC Studio.

## Focused selector regression

Run `scripts/test_select_changed_tests.py` to verify backend, frontend, edited-test, combined, docs-only and fallback cases. The runner regression verifies the updated switch wiring. Check `-SkipUpdate -ChangedTests` and existing `-SkipTests` behavior.
ESP firmware does not require reflashing. `0_3_11` remains the passed baseline until explicit owner PASS.
