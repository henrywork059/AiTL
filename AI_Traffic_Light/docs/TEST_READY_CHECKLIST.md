# V0316 Test-Ready Checklist

```text
version: 0_3_16
previous_version: 0_3_15
passed_baseline: 0_3_11
status: focused startup validation candidate
```

## Changed-tests startup

- [ ] `-ChangedTests` passes through the one-time Git pull/reload.
- [ ] Known backend changes select related offline regressions.
- [ ] Frontend changes retain typecheck/build.
- [ ] Shared/unknown and dependency changes trigger full fallback.
- [ ] No-update mode targets the latest commit.
- [ ] Structure/version checks and runner regression remain mandatory.
- [ ] Backend health and live smoke remain mandatory.
- [ ] Other port owners and user runtime data are protected.

## Full acceptance

- [ ] Default startup runs complete offline regression suite.
- [ ] Frontend typecheck/build and Git cleanliness succeed.
- [ ] PC Studio opens; camera/simulation and app functionality work.
- [ ] Explicit owner PASS received before promoting the baseline.

`0_3_11` remains the passed baseline.
