# Start Here — V0313

V0313 / `0_3_13` is the current code-management and optimization candidate. V0312 / `0_3_12` is the previous unaccepted candidate. V0311 / `0_3_11` remains the owner-confirmed passed baseline until explicit V0313 acceptance.

## Normal Windows workflow

Use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The helper fast-forwards `origin/main`, reloads the pulled runner once, runs compile/structure-release/regression/frontend checks, safely replaces only AiTL-owned PC Studio listeners on ports 8000/5173, runs live smoke, and opens PC Studio. Untracked runtime/user data is preserved.

If the backend `.venv` does not exist, run `scripts/setup_backend_windows.ps1` once and retry.

## V0313 scope

V0313 manages and optimizes existing code rather than adding a new functional capability:

- Junction Network page state remains in `JunctionNetworkPage.tsx` while node presentation and pure view helpers now have narrow modules;
- repeated frontend link/source lookups use memoized maps;
- saved ESP camera view projection is performed once per Junction Network overview poll and reused;
- `scripts/check_structure.py` is the single structural/release-consistency authority;
- the duplicate release-consistency regression and duplicate runner step are removed;
- durable coding/playbook guidance now guards these ownership and validation rules.

## Functional boundary

Junction Network behavior remains the same: a junction may own multiple saved cameras, a source remains exclusive to one junction, and exactly one selected physical/simulation source feeds the shared live inference/traffic pipeline. Unobserved junctions do not receive fabricated live counts.

The V0312 non-clipping junction-card layout is preserved.

V0310 remains the production ESP32-CAM path using FB1 + `CAMERA_GRAB_LATEST`, bounded plain `send()` writes and the unchanged `ATL1` / `aitl-tcp-jpeg-v1` contract.

AiTL remains a local/student-scale prototype; physical/public-road traffic-signal authority is out of scope.
