# Start Here — V0314

V0314 / `0_3_14` is the current frontend-polling reliability and code-optimization candidate. V0313 / `0_3_13` is the previous unaccepted candidate. V0311 / `0_3_11` remains the owner-confirmed passed baseline until explicit V0314 acceptance.

## Normal Windows workflow

Use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The helper fast-forwards `origin/main`, reloads the pulled runner once, runs compile/structure-release/regression/frontend checks, safely replaces only AiTL-owned PC Studio listeners on ports 8000/5173, runs live smoke, and opens PC Studio. Untracked runtime/user data is preserved.

If the backend `.venv` does not exist, run `scripts/setup_backend_windows.ps1` once and retry.

## V0314 scope

V0314 follows a current-main whole-project audit. The concrete reliability defect found was overlapping async frontend polling: six pages still used `window.setInterval` around API work even though `useSerialPolling` already provides settled-task scheduling.

Those pages now use the shared serial hook, Traffic Analytics preserves immediate refresh when its query changes, and startup/status polling errors are handled rather than leaking rejected promises. The structural validator now rejects future `window.setInterval` usage anywhere in frontend TypeScript/TSX source.

No backend API, signal/safety policy, stored schema, ESP transport, dataset, training or inference behavior was reconstructed because no verified defect required it.

## Functional boundary

The existing single-selected-source live observation model remains unchanged: only the resolved physical/simulation source feeds current live inference/traffic state. Signal-control capability remains simulation/prototype only and does not provide public-road controller authority.

V0310 remains the production ESP32-CAM path using FB1 + `CAMERA_GRAB_LATEST`, bounded plain `send()` writes and the existing `ATL1` / `aitl-tcp-jpeg-v1` contract.
