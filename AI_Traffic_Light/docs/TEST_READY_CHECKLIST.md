# V0312 Test-Ready Checklist

Release state:

```text
version: 0_3_12
previous_version: 0_3_11
passed_baseline: 0_3_11
status: repository cleanup candidate
```

V0312 remains unaccepted until the owner explicitly confirms PASS.

## Automated validation

- [ ] Normal Windows command performs one update/reload cycle only.
- [ ] Recursive reload guard regression passes.
- [ ] Python compile passes.
- [ ] Repository structure/current-release consistency passes.
- [ ] Automatic zero-argument backend regressions pass.
- [ ] Junction Network frontend structure/content-visibility regression passes.
- [ ] Frontend typecheck passes.
- [ ] Frontend production build passes.
- [ ] Git tracked-cleanliness check passes.
- [ ] Live backend smoke passes.

## Cleanup validation

- [ ] No root `PATCH_MANIFEST_*` files remain.
- [ ] No root `PATCH_APPLY_INSTRUCTIONS_*` files remain.
- [ ] Historical `docs/PATCH_*` and cumulative changelog history remain available.
- [ ] V036 metadata finalizer and its preservation-only regression are removed.
- [ ] Duplicate generic Windows backend/frontend launch wrappers are removed.
- [ ] Obsolete V010 test-ready instructions and old smoke `.bat` wrapper are removed.
- [ ] V0310 production firmware remains available.
- [ ] V037 source remains available because V0310 still inherits it.
- [ ] Camera diagnostic firmware/tools remain available.
- [ ] First-time/recovery `setup_backend_windows.ps1` remains available.

## Functional regression

- [ ] Junction Network still loads/persists nodes, links and camera assignments.
- [ ] Junction cards show the full title/ACTIVE state, vehicle/pedestrian load, phase and event/warning badges without clipping inside the node.
- [ ] Long junction labels/status values wrap inside the node rather than disappearing past its border.
- [ ] Only the selected source feeds the shared live inference/traffic pipeline.
- [ ] Dataset/training/inference/model workflows remain unchanged.
- [ ] Simulation/adaptive signal behavior remains unchanged.
- [ ] V0310 `ATL1` production camera path remains unchanged.
- [ ] Runtime/user data is not deleted by the runner.
- [ ] No physical/public-road signal-control authority is introduced.

After these checks, explicit owner confirmation is required before changing `passed_baseline` from `0_3_11`.
