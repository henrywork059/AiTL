# Local Testing — V0311

Expected release state:

```text
version: 0_3_11
previous_version: 0_3_10
passed_baseline: 0_3_11
status: owner-confirmed passed baseline
```

## Normal update / test / run

Use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The runner performs:

```text
fast-forward main
→ reload pulled runner
→ Python compile
→ structure/current-release/runner preflight checks
→ refresh backend dependencies only when requirements changed
→ automatic zero-argument offline regressions
→ refresh frontend dependencies only when package manifests changed or node_modules is missing
→ frontend typecheck/build
→ Git cleanliness
→ safely replace only AiTL-owned PC Studio processes
→ live backend smoke
→ launch frontend/backend
```

Skipping unchanged dependency installation does **not** skip regressions, typecheck, build or smoke.

Force dependency refresh only when needed:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -RefreshDependencies
```

## V0311 regression coverage

The normal runner auto-discovers ordinary zero-argument `scripts/test_*.py` regressions. Important V0311 checks include:

- `test_release_documentation_consistency.py` — release/document/playbook/architecture consistency;
- `test_update_test_run_script.py` — runner safety, preflight ordering, dependency optimization and automatic test discovery;
- `test_intersection_network.py` — junction layout, multi-camera assignment, source exclusivity, backward schema handling and explicit-null primary-camera persistence;
- `test_junction_network_overview.py` — camera health, selected-source observation mapping, traffic/pedestrian load, events/warnings and unavailable non-selected junctions;
- `test_junction_network_frontend_structure.py` — navigation, App routing, function registry, serial polling, typed API/types and visualization wiring.

Hardware/interactive camera utilities remain outside the ordinary no-hardware regression sweep.

## Confirmed V0311 acceptance

On 2026-09-01 the owner confirmed V0311 is running correctly and passes. The following behaviors are therefore part of the passed baseline:

- Junction Network loads and persists its node/link configuration;
- multiple saved ESP cameras may be assigned to one junction;
- one camera/source remains exclusive to one junction;
- Primary camera may intentionally be set to None and persist as null;
- only the junction resolved from the shared selected source receives live AI/simulation traffic metrics;
- other junctions show unavailable live load rather than copied/fabricated values;
- V0310 production camera transport remains active;
- the normal update/test/run workflow is the standard owner validation/startup path.

## Future patch testing

Future work should start from `0_3_11` as the passed baseline. When a new patch is explicitly requested, follow `docs/PATCH_PLAYBOOK.md`, add focused zero-argument regressions where practical, and continue using the same normal runner command for full validation.

AiTL remains a local/student-scale prototype. Physical/public-road traffic-control authority remains out of scope.
