# Local Testing — V0311

Expected release state:

```text
version: 0_3_11
previous_version: 0_3_10
passed_baseline: 0_2_4
```

## Normal update / test / run

Use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The normal command still performs the full validation/startup workflow, but repeated runs are faster:

```text
fast-forward main
→ reload pulled runner
→ Python compile
→ project/current-release/runner preflight checks
→ refresh backend dependencies only if requirements changed
→ automatic offline regressions
→ refresh frontend dependencies only if package manifests changed or node_modules is missing
→ frontend typecheck/build
→ Git cleanliness
→ safely replace only AiTL-owned PC Studio processes
→ live backend smoke
→ launch frontend/backend
```

Skipping unchanged dependency installation does **not** skip regressions, typecheck, build or smoke.

If the local dependency environment was manually damaged or you suspect it is inconsistent, force refresh with:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -RefreshDependencies
```

Direct `-SkipUpdate` runs refresh dependencies conservatively because they have no Git update diff to prove manifests were unchanged.

You should not need a separate list of newly added offline tests: the runner discovers zero-argument `scripts/test_*.py` by naming convention. Hardware/interactive camera utilities remain separate from that sweep.

## Focused V0311 offline checks

The normal runner should include:

- `scripts/test_release_documentation_consistency.py` — current/previous/passed-baseline docs, frontend version, VERSION-last playbook safeguards and durable production architecture markers;
- `scripts/test_update_test_run_script.py` — fast-forward/read-only/restart behavior, cheap-preflight ordering, dependency-manifest optimization, automatic regression discovery and hardware-test separation;
- `scripts/test_intersection_network.py` — V0311 position/primary-source/backward-schema/source-exclusivity assertions including explicit-null persistence;
- `scripts/test_junction_network_overview.py` — multi-camera junction assignment, camera health, live observation mapping/events/warnings and unavailable non-selected junctions;
- `scripts/test_junction_network_frontend_structure.py` — navigation, `App.tsx`, function registry, serial polling, typed API/types and node/link/load/warning UI wiring.

`check_structure.py` should also fail early if current-candidate docs drift, Junction Network/playbook files disappear, intersection config stops using the atomic JSON writer, Junction Network polling becomes overlapping, or durable camera architecture returns to the obsolete two-framebuffer claim.

Expected semantic checks:

- a junction accepts multiple `source_ids` but a source cannot remain assigned to two junctions simultaneously;
- `primary_source_id` is null or one of the junction's own `source_ids`;
- an explicit `primary_source_id: null` remains null after save/reload;
- an older schema-1 junction that **omits** `primary_source_id` still receives the first assigned source as its migration default;
- canvas positions persist as finite 0–100 logical percentage coordinates;
- older schema-1 configs without V0311 layout metadata receive deterministic defaults;
- `GET /api/traffic/network/overview` is wired through the dedicated overview service and standard API envelope/request-ID behavior;
- saved ESP camera health is visible while live traffic/pedestrian metrics apply only to the junction resolved from the current shared selected source;
- non-selected/unobserved junctions report unavailable occupancy/load rather than copied counts;
- Junction Network is present in navigation **and** the central function registry;
- durable architecture identifies the real production camera path as FB1 + `CAMERA_GRAB_LATEST`, not the obsolete two-framebuffer description;
- existing camera/session, simulation, inference, dataset, analytics, signal-rule and network-experiment regressions remain passing.

## PC Studio V0311 acceptance test

1. Run the normal one-command workflow and confirm all automated checks pass.
2. Open **Traffic → Junction Network**.
3. Confirm the current `config/intersections.json` network is visible.
4. Add at least two junctions and drag them to clearly different canvas positions.
5. Add a directed line between two junctions, set its travel time and save.
6. Assign two saved ESP cameras to one junction. Confirm another junction cannot silently retain the same source; use the explicit reassignment flow if needed.
7. Choose one assigned camera as the primary source and save.
8. Change **Primary camera** to **None**, save, restart PC Studio, and verify it stays None rather than reverting to the first assigned camera.
9. Verify node positions, links and camera assignments also persist after restart.
10. Select/start one ESP in Camera Sources and verify the corresponding junction can show current live traffic/pedestrian state when inference/simulation observations are available.
11. Confirm another unselected junction shows unavailable load instead of mirroring the selected junction.
12. Disconnect or make an assigned ESP unavailable and confirm a warning appears in Junction Network.
13. Exercise an existing ranked scenario, pedestrian-service request or manual/test event and confirm the observation junction displays the event with correct prototype provenance.
14. Confirm Dashboard/function-status presentation includes Junction Network capabilities.
15. Verify Camera Sources, Live AI, Camera Diagnostics, Traffic Logic, Analytics, Dataset Capture/Review, Training, Models and Simulation Lab still open and behave normally.
16. Run the same normal command once more with no dependency-manifest changes. Confirm it reports backend/frontend dependency refresh as skipped but still completes regressions, frontend checks, smoke and startup.

## Faster failure reporting

If the runner fails, copy the **first failed section and its error**. Cheap repository/release checks now run before dependency installation, so version/document/runner mistakes should be visible near the top.

Do not rerun unrelated individual tests first. Use an individual command only for the failed stage. If the failure is a missing/broken package, retry once with `-RefreshDependencies`.

## V0310 camera regression remains applicable

V0311 does not change ESP firmware or the V0310 production camera transport. If continuing physical camera validation, keep using:

```text
apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino
```

The existing approximately 10–12 FPS production acceptance target at the known-good Wi-Fi position remains a V0310 camera-transport check, separate from V0311 Junction Network acceptance.

V024 / `0_2_4` remains the passed baseline until explicit owner acceptance. Physical/public-road traffic-control authority remains out of scope.
