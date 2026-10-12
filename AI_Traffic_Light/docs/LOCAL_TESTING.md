# Local Testing — V0322

```text
version: 0_3_22
previous_version: 0_3_21
passed_baseline: 0_3_11
status: Windows fresh-install dependency fix candidate
```

## Focused verification

1. Confirm backend `requirements.txt` includes `httpx==0.28.1`.
2. Verify the existing `scripts/update_test_run.ps1` refreshes backend dependencies when requirements change.
3. Run `python scripts/test_camera_simulation_api.py` from `AI_Traffic_Light` using `apps/pc-studio/backend/.venv/Scripts/python.exe`, and ensure `fastapi.testclient.TestClient` imports without `ModuleNotFoundError: httpx`.
4. Run `python scripts/check_structure.py`, then the full Windows `scripts/update_test_run.ps1` acceptance suite. Backend smoke, frontend build and actual app startup still need owner confirmation.

No backend functional changes, security changes or new features. `0_3_11` remains the accepted baseline.
