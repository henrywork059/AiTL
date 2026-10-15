# Patch 0_4_7 — Safe Windows Uvicorn worker restart

Previous candidate `0_4_6`. Owner-accepted stable baseline `0_4_0`.

## Observed failure

The V0406 Windows update/test/run completed structure and focused regressions but then refused to stop `python.exe` PID 35864 on port 8000. This safety refusal is correct when the owner is unknown. However, Windows Uvicorn `--reload` starts a worker through `multiprocessing.spawn`; the listener's command line may show `spawn_main` instead of `uvicorn`.

## Minimal change

The runner now recognizes a spawned backend worker only if its Python executable exactly matches the AiTL backend virtual environment, its worker command line contains `spawn_main` and `--multiprocessing-fork`, and its parent belongs to the same virtual environment and runs `uvicorn app.main:app --reload --port 8000`. Only the verified Uvicorn Python tree is terminated; parent PowerShell is not killed. If the evidence is unavailable or a different Python program owns the port, startup still stops safely.

No backend services, frontend application, camera transport, traffic logic or dependencies changed.

## Validation

Extended the updater's regression assertions to protect the worker-parent identity check and avoid killing its host shell. Static source-level checks are available. Actual Windows process behavior, `/health` and UI startup require owner testing.

Use the standard one-line updater:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
