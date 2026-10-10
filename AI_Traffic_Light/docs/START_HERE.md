# Start Here — V0316

V0316 / `0_3_16` adds an opt-in focused startup test option. Previous version: `0_3_15` (unaccepted). Passed baseline: `0_3_11`.

## Full startup (default)

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

## Fast startup (changed code tests)

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Both commands update from `origin/main`, reload the current runner once, validate structure/release and runner safety, safely restart only AiTL-owned PC Studio processes, run backend health/smoke and open the app.
The faster option selects relevant offline regressions and only builds the frontend when frontend files change. Shared/unknown changes fall back to the full suite. No application or firmware behavior changed.
