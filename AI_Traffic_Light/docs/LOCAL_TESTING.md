# Local Testing — V0312

Expected release state:

```text
version: 0_3_12
previous_version: 0_3_11
passed_baseline: 0_3_11
status: repository cleanup candidate
```

## Normal update / test / run

From any PowerShell directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Expected sequence:

```text
fast-forward main
→ reload pulled runner exactly once
→ Python compile
→ structure/current-release/runner preflight checks
→ dependency refresh only when manifests changed
→ automatic zero-argument offline regressions
→ frontend typecheck/build
→ Git tracked-cleanliness check
→ safely replace only AiTL-owned PC Studio listeners
→ live backend smoke
→ launch frontend/backend
```

A normal run must show only one `=== Update from origin/main ===` section. If parameter binding ever regresses, `AITL_RUNNER_RELOADED` must stop execution with `Recursive update prevented` instead of looping.

Force dependency refresh only when needed:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -RefreshDependencies
```

## V0312 checks

Confirm:

- `scripts/test_update_test_run_script.py` passes the explicit reload/recursion guard checks;
- structure and release-document consistency pass for `0_3_12` / previous `0_3_11` / baseline `0_3_11`;
- all remaining ordinary `scripts/test_*.py` regressions pass;
- frontend typecheck and production build pass;
- live backend smoke passes;
- the frontend opens normally;
- running the same command again safely replaces only AiTL-owned ports 8000/5173;
- runtime data under config/datasets/outputs and generated caches is not deleted.

## Functional regression boundary

V0312 should not change V0311 Junction Network behavior, the single-selected-source live inference boundary, simulation/signal logic, dataset/training/inference APIs, or V0310 production camera transport.

`0_3_11` remains the passed baseline until the owner explicitly confirms V0312 passes.
