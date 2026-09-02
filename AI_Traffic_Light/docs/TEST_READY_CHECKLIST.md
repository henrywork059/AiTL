# V0313 Test-Ready Checklist

Release state:

```text
version: 0_3_13
previous_version: 0_3_12
passed_baseline: 0_3_11
status: code management and optimization candidate
```

V0313 remains unaccepted until the owner explicitly confirms PASS.

## Automated validation

- [ ] Python compile passes.
- [ ] `check_structure.py` passes as the single structure/release-consistency authority.
- [ ] Runner self-regression passes and confirms the duplicate release-consistency step is absent.
- [ ] Junction Network overview optimization regression passes.
- [ ] Junction Network frontend modularity/content-visibility regression passes.
- [ ] All remaining automatic zero-argument backend regressions pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend production build passes.
- [ ] Git tracked-cleanliness check passes.
- [ ] Live backend smoke passes.

## Code management validation

- [ ] `JunctionNetworkPage.tsx` owns page state/mutations rather than node-card presentation.
- [ ] `components/junctions/JunctionNodeCard.tsx` owns node-card presentation only.
- [ ] `lib/junctionNetworkView.ts` owns pure view/config helpers.
- [ ] Repeated link/source lookups use memoized maps in the Junction Network page.
- [ ] Saved ESP camera UI projections are created once per overview and reused.
- [ ] `scripts/test_release_documentation_consistency.py` is absent.
- [ ] `scripts/check_structure.py` contains the consolidated durable release/workflow checks.
- [ ] Normal runner has one `Project structure and release consistency` preflight plus its self-regression.

## Functional regression

- [ ] Junction Network loads/persists nodes, links and camera assignments unchanged.
- [ ] Junction cards retain the V0312 non-clipping layout for long titles/status values.
- [ ] Camera reassignment and Primary camera/None persistence remain correct.
- [ ] Only the selected source feeds the shared live inference/traffic pipeline.
- [ ] Dataset/training/inference/model workflows remain unchanged.
- [ ] Simulation/adaptive signal behavior remains unchanged.
- [ ] V0310 `ATL1` production camera path remains unchanged.
- [ ] Runtime/user data is preserved by the runner.
- [ ] No physical/public-road signal-control authority is introduced.

After these checks, explicit owner confirmation is required before changing `passed_baseline` from `0_3_11`.
