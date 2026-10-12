# PATCH_0_3_22 — Missing fresh-install test dependency

Version: `0_3_22`  
Previous candidate: `0_3_21`  
Passed baseline: `0_3_11` (unchanged)

## Fix

- Add `httpx==0.28.1` to the pinned backend requirements. `fastapi.testclient.TestClient` depends on `httpx`; clean Windows virtual environments previously failed at `scripts/test_camera_simulation_api.py`.
- Reuse the existing updater's dependency refresh when requirements change. No runtime/API, streaming, UI, firmware or signal behavior changes.

## Validation

- Confirm `httpx` appears once in base requirements and `requirements-training.txt` includes the base requirements.
- Run `python scripts/test_camera_simulation_api.py`, `python scripts/check_structure.py` and the full `scripts/update_test_run.ps1` on Windows.
- The agent can inspect the manifest/commit; it cannot verify the user's new PC virtual environment or full Windows installation.

`0_3_11` remains the owner-confirmed passed baseline pending explicit PASS.
