# Start Here — V0315

V0315 / `0_3_15` is the current concurrency-hardening and conflict-cleanup candidate. V0314 / `0_3_14` is the previous unaccepted candidate. V0311 / `0_3_11` remains the owner-confirmed passed baseline.

## Normal Windows workflow

```powershell
& "C:\Users\henry_sik0ar\Downloads\AiTL_app\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The runner fast-forwards `origin/main`, reloads itself once, runs compile/structure/regression/frontend checks, safely replaces only AiTL-owned PC Studio listeners, runs live backend smoke and opens PC Studio.

## V0315 scope

The follow-up audit found an internal concurrency gap in V0314: timer polling was serial, but effect restarts, manual refreshes and mutations could still overlap an in-flight status request.

V0315 makes the shared polling helper single-flight across all of those entry points and removes the duplicate Live AI page-local detection loop. State-changing operations now pause/drain conflicting status polling where stale reads could overwrite fresh state.

Files that looked redundant but are active dependencies—V0310/V037 firmware compatibility sources, frontend fallback fixtures, Simulation Lab API code and camera diagnostic modules—were retained.

Backend APIs, safety logic, persistence, simulation semantics, model/data contracts and the production ATL1 transport remain unchanged.
