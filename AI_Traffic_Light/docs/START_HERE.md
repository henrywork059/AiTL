# Start Here — V0322

V0322 / `0_3_22` fixes the missing `httpx` dependency in fresh Windows PC Studio installations. Previous candidate: `0_3_21` (unaccepted). Owner-confirmed passed baseline: `0_3_11`.

## Fix

Backend requirements now include `httpx==0.28.1`, needed by FastAPI's `TestClient` regressions. The update/test/run script installs it automatically when pulling this requirements change. All existing Crosswalks and Camera Settings behavior remains unchanged.

## On the new Windows PC

```powershell
& "D:\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Run with `-RefreshDependencies` if dependency installation was previously interrupted or the script does not detect a requirements change. Owner PASS requires full validation; `0_3_11` remains the accepted baseline.
