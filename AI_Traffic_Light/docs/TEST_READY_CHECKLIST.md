# V0315 Test-Ready Checklist

Release state:

```text
version: 0_3_15
previous_version: 0_3_14
passed_baseline: 0_3_11
status: concurrency hardening and conflict cleanup candidate
```

## Automated

- [ ] Python compile passes.
- [ ] Structure/release validation passes.
- [ ] Frontend polling single-flight regression passes.
- [ ] All automatic backend regressions pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend production build passes.
- [ ] Git cleanliness check passes.
- [ ] Live backend smoke passes.

## Conflict / stability

- [ ] One in-flight request is shared across timer ticks, restarts and manual refresh.
- [ ] Live AI has no separate page-local detection polling timer.
- [ ] Logs manual refresh shares the periodic request owner.
- [ ] Dataset capture/delete cannot race a stale dataset-status response.
- [ ] Analytics clear cannot be overwritten by an older analytics response.
- [ ] Training start cannot be overwritten by an older training-status response.
- [ ] Camera mode switching cannot race camera-status polling.
- [ ] Polling resumes after failures and after mutations complete.

## Cleanup

- [ ] No `window.setInterval` remains in frontend TS/TSX.
- [ ] V0310/V037 firmware compatibility sources remain because they are active build dependencies.
- [ ] Fallback fixture, Simulation Lab API and diagnostic helper modules remain because they are referenced.
- [ ] No runtime/user data is removed.

Explicit owner PASS is required before changing `passed_baseline` from `0_3_11`.
