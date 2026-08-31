# Local Testing — V039

Expected release state:

```text
version: 0_3_9
previous_version: 0_3_8
passed_baseline: 0_2_4
```

## Normal update / test / run

Use the same command for routine validation and launch from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The helper should:

1. require local `main` and refuse tracked local edits;
2. fast-forward from `origin/main`;
3. reload the newly pulled helper;
4. refresh backend/training/frontend dependencies as required;
5. run Python compile, structure validation, backend regressions, frontend typecheck/build, Git whitespace/cleanliness checks and live backend smoke;
6. before startup, inspect listeners on ports 8000 and 5173;
7. stop a listener only when Win32 process evidence identifies it as this repository's AiTL PC Studio backend/frontend process tree;
8. refuse to terminate an unrelated listener;
9. start the backend on 8000 and frontend on 5173, wait for readiness and open PC Studio.

If a patch was deliberately overlaid directly onto the local working tree, `-SkipUpdate` remains available. `-SkipTests` is for a deliberate fast relaunch after the same code has already been validated; it is not the normal acceptance path.

## Focused V039 checks

- Start PC Studio normally, then run the canonical command again without manually killing the existing backend/frontend.
- Confirm the old AiTL-owned processes are identified and stopped automatically.
- Confirm the replacement backend becomes healthy on `http://127.0.0.1:8000/health` and the frontend becomes available on port 5173.
- Confirm the live backend smoke test runs after backend readiness during a normal full test run.
- Confirm runtime/user data such as `datasets/`, `outputs/`, saved camera/signal configuration, model weights, `.venv`, `node_modules`, `dist` and caches are not deleted.
- Confirm an unrelated process deliberately placed on port 8000 or 5173 is not terminated automatically; the helper must stop with a clear ownership/safety error instead.
- Confirm `scripts/test_update_test_run_script.py` passes the ownership/restart guardrails.

## Retained V038/R10 camera checks

V039 does not change Camera Diagnostics. With the matching diagnostic firmware flashed, **Operate → Camera Test → Diagnose camera** still runs the adaptive R5/R8/R9/R10 diagnostic path. R10 retains the framebuffer/grab-mode/FPS matrix, newest-frame cache comparison, JPEG-quality sweep, TCP write-size/transfer-size/repeatability tests and exact diagnostic state restoration.

Existing Camera Sources, Live AI, simulation, Dataset Capture, multi-ESP selection, training/inference, network-simulation experiments and the prototype-only safety boundary must remain intact.
