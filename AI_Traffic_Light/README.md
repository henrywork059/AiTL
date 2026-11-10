# AI Traffic Light (AiTL)

AiTL is a local/student-scale computer-vision and adaptive traffic-light simulation prototype. It combines a Windows PC Studio application with ESP32-CAM camera nodes, simulation, dataset/training tools, traffic analytics, configurable signal logic, and multi-junction visualization.

The authoritative release state is always in [`VERSION`](VERSION). Current-candidate details belong in `docs/PATCH_<version>.md`; durable architecture and workflow rules belong in the `docs/` guides.

## PC Studio

- FastAPI backend
- React/Vite frontend
- camera receiver and simulation source
- ESP32-CAM profile/session management
- live AI inference with trained YOLO models
- dataset capture, review, labeling and managed training
- occupancy, tracking and traffic-flow analytics
- configurable protected signal timing and adaptive scenario logic
- deterministic simulation experiments
- Junction Network configuration and visualization
- decision/explainability evidence for simulation/network experiments

Exactly one selected physical or simulation source currently feeds the shared live inference/traffic pipeline. Junction Network may represent and configure multiple junctions/cameras, but it does not claim simultaneous live inference at every junction.

## ESP32-CAM

The active production camera path is the V0310-tuned ESP32-CAM implementation. It preserves the `aitl-tcp-jpeg-v1` / `ATL1` framing contract, uses one framebuffer with `CAMERA_GRAB_LATEST`, and retains PC-owned image quality/resolution/FPS settings. Diagnostic firmware remains separate from the production entrypoint.

## Windows workflow

After first-time backend setup, normal update/test/run is one command from any PowerShell directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The runner fast-forwards `origin/main`, protects tracked local work, preserves untracked runtime data, reloads the pulled runner once, runs structure/regression/frontend checks and live smoke, safely replaces only AiTL-owned PC Studio processes on ports 8000/5173, and opens PC Studio.

For faster routine startup with focused checks, add the optional `-ChangedTests` switch:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

This selects tests for changed code instead of the entire offline suite; shared/unknown changes fall back to full validation. Structure and health checks remain active. Use the default command for comprehensive regression validation.

First-time backend environment setup/recovery:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\setup_backend_windows.ps1"
```

## Testing an unaccepted feature branch

The normal Windows runner updates `main` and refuses to run with automatic update from a different branch. To test candidate `feature/interactive-3d-simulation`, first ensure the working tree is clean, then execute from the repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

If the branch is not yet present locally, use `git switch --track origin/feature/interactive-3d-simulation`. Read `VERSION` and `docs/PATCH_<version>.md` for the current candidate and its acceptance tests. The `-SkipUpdate` flag avoids pulling `main`; it does not constitute owner PASS.

## Documentation

Start with:

- `docs/START_HERE.md`
- `docs/DOCUMENTATION_MAP.md`
- `docs/PROJECT_SCOPE.md`
- `docs/ARCHITECTURE.md`
- `docs/PATCH_PLAYBOOK.md`
- `docs/LOCAL_TESTING.md`
- `docs/TEST_READY_CHECKLIST.md`

## Safety boundary

AiTL is a prototype for simulation, model-junction demonstrations and controlled hardware experiments. It does not provide certified or authorized physical/public-road traffic-signal control.
