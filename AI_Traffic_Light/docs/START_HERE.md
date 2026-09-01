# Start Here — V0312

V0312 / `0_3_12` is the current cleanup candidate. V0311 / `0_3_11` is the previous version and remains the owner-confirmed passed baseline until explicit V0312 acceptance.

## Normal Windows workflow

Use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The helper fast-forwards `origin/main`, reloads the pulled script exactly once, runs compile/structure/regression/frontend checks, safely replaces only AiTL-owned PC Studio listeners on ports 8000/5173, runs live smoke, and opens PC Studio. Untracked runtime/user data is preserved.

If the backend `.venv` does not exist, run `scripts/setup_backend_windows.ps1` once and retry.

## V0312 scope

V0312 is maintenance-only:

- removes obsolete patch manifests/apply instructions and duplicate Windows wrappers;
- removes the historical V036 metadata finalizer and archived V036 standalone firmware path that are no longer active;
- keeps V0310 production firmware, inherited V037 source, diagnostics, current APIs and runtime data;
- replaces the stale release-specific README with a durable project overview;
- hardens the Windows runner against recursive self-reload.

## Active functional baseline

V0311 Junction Network behavior remains unchanged: multiple saved cameras may be assigned to a junction, one source remains exclusive to one junction, and exactly one selected physical/simulation source feeds the shared live inference/traffic pipeline. Unobserved junctions do not receive fabricated live counts.

V0310 remains the production ESP32-CAM path using FB1 + `CAMERA_GRAB_LATEST`, bounded plain `send()` writes and the unchanged `ATL1` / `aitl-tcp-jpeg-v1` contract.

AiTL remains a local/student-scale prototype; physical/public-road traffic-signal authority is out of scope.
