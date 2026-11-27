# Patch 0_5_30 — One protected signal snapshot per simulation substep

**Candidate:** `0_5_30` | **Previous:** `0_5_29` | **Accepted baseline:** `0_5_0` | **Branch:** `feature/interactive-3d-simulation`

## Optimization

Previously, in each maximum-50 ms simulation substep, `CameraFrameService` queried `SignalRulesService.signal_state` separately for vehicle and pedestrian movement, even though both used the same simulation clock. Because this signal evaluation is **stateful** (phase progression and configured scenarios), the duplicate work also meant each agent type read a separate evaluation.

The integrator now queries the protected controller **once per substep**, passes the returned phase to both movement helpers and keeps all phase-state ownership in `signal_rules.py`. In an uninterrupted 200 ms advance, the query count falls from eight to four. This is a verified code-path reduction, **not** a claim of measured latency, frame-rate or CPU improvement.

## Compatibility and safety

Vehicle queues still obey stop lines, and pedestrians still enter only on WALK. Yellow, all-red, pedestrian-clear and configured scenario logic continue to be resolved by the existing controller. No public API, persisted configuration, schema, synthetic frame encoding, 3D camera coordinate system, live inference, physical ESP transport, virtual network interlock or physical-signal output changes. The prior `0_5_29` BGR mirror-render optimization remains intact.

## Regression and validation

- `python scripts/test_camera_frame_service.py`: exact one protected phase evaluation per 50 ms substep, plus existing vehicle/pedestrian safety, pause/resume and camera-render regressions.
- `python scripts/test_signal_rules_service.py`: rule evaluation, protected phase evolution, input and backward-clock behavior.
- `python scripts/test_camera_simulation_api.py`, `python scripts/test_v0515_3d_simulation.py`: camera HTTP/3D continuity.
- Full candidate CI: Python compile, structure/version rules, offline regression suite, frontend TypeScript typecheck and production build.
- Owner Windows checks: check phase transitions and absence of conflicting vehicle/pedestrian movement, all synthetic views, pause/resume/density and unaffected real ESP preview. Explicit owner PASS is required.

## Feature-branch pull/test

The default helper updates `main`; to validate this unaccepted feature branch, use a **clean** working tree and run from the repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

If the local branch is new, first use `git switch --track origin/feature/interactive-3d-simulation`. No promotion, merge or physical signal-control enablement is included in this patch.
