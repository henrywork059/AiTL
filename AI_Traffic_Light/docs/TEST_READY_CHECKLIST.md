# V0314 Test-Ready Checklist

Release state:

```text
version: 0_3_14
previous_version: 0_3_13
passed_baseline: 0_3_11
status: frontend polling reliability and code optimization candidate
```

V0314 remains unaccepted until the owner explicitly confirms PASS.

## Automated validation

- [ ] Python compile passes.
- [ ] `check_structure.py` passes.
- [ ] Frontend polling regression passes across every registered periodic surface.
- [ ] All remaining automatic zero-argument backend regressions pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend production build passes.
- [ ] Git tracked-cleanliness check passes.
- [ ] Live backend smoke passes.

## Reliability validation

- [ ] Frontend TypeScript/TSX source contains no `window.setInterval`.
- [ ] Camera Diagnostics progress polling is serial/non-overlapping.
- [ ] Dataset Capture status polling is serial and reports refresh errors.
- [ ] Live AI status polling is serial and initialization failures are handled.
- [ ] Logs polling is serial/non-overlapping.
- [ ] Traffic Analytics polling is serial and filter/query changes refresh immediately.
- [ ] Train / Export status polling is serial and runtime/status errors are handled.
- [ ] Existing settled-task Live AI detection polling remains non-overlapping.

## Functional regression

- [ ] Camera/source/simulation workflows remain unchanged.
- [ ] Traffic history/flow and analytics filters remain correct.
- [ ] Dataset capture/delete/review and labels remain correct.
- [ ] Training/inference/model workflows remain correct.
- [ ] Junction Network behavior remains unchanged.
- [ ] Signal simulation and safety-transition behavior remain unchanged.
- [ ] V0310 `ATL1` production camera transport remains unchanged.
- [ ] Runtime/user data is preserved by the runner.
- [ ] No physical/public-road signal-control authority is introduced.

After these checks, explicit owner confirmation is required before changing `passed_baseline` from `0_3_11`.
