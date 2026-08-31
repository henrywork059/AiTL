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

The helper should fast-forward `main`, reload itself, refresh dependencies, run Python compile/structure and every automatic zero-argument `scripts/test_*.py` regression, frontend typecheck/build, Git cleanliness and live backend smoke, safely replace an existing AiTL-owned PC Studio instance on ports 8000/5173, and relaunch the app. Unrelated port owners remain protected.

You should not need a separate list of newly added offline tests: the runner discovers them by naming convention. Hardware/interactive camera utilities remain separate from the zero-argument sweep.

## Focused V0311 offline checks

The normal runner should include:

- `scripts/test_release_documentation_consistency.py` — current/previous/passed-baseline docs, frontend version, VERSION-last playbook safeguards and durable production architecture markers;
- `scripts/test_update_test_run_script.py` — fast-forward/read-only/restart behavior plus automatic regression discovery and hardware-test separation;
- `scripts/test_intersection_network.py` — V0311 position/primary-source/backward-schema/source-exclusivity assertions;
- `scripts/test_junction_network_overview.py` — multi-camera junction assignment, camera health, live observation mapping/events/warnings and unavailable non-selected junctions;
- `scripts/test_junction_network_frontend_structure.py` — navigation, `App.tsx`, function registry, serial polling, typed API/types and node/link/load/warning UI wiring.

Expected semantic checks:

- a junction accepts multiple `source_ids` but a source cannot remain assigned to two junctions simultaneously;
- `primary_source_id` is null or one of the junction's own `source_ids`;
- canvas positions persist as finite 0–100 logical percentage coordinates;
- older schema-1 configs without V0311 layout/primary-source metadata receive deterministic defaults;
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
8. Restart PC Studio and verify node positions, links, camera assignments and primary camera persist.
9. Select/start one ESP in Camera Sources and verify the corresponding junction can show current live traffic/pedestrian state when inference/simulation observations are available.
10. Confirm another unselected junction shows unavailable load instead of mirroring the selected junction.
11. Disconnect or make an assigned ESP unavailable and confirm a warning appears in Junction Network.
12. Exercise an existing ranked scenario, pedestrian-service request or manual/test event and confirm the observation junction displays the event with correct prototype provenance.
13. Confirm Dashboard/function-status presentation includes Junction Network capabilities.
14. Verify Camera Sources, Live AI, Camera Diagnostics, Traffic Logic, Analytics, Dataset Capture/Review, Training, Models and Simulation Lab still open and behave normally.

## Faster failure reporting

If the runner fails, copy the **first failed section and its error**. Do not rerun unrelated individual tests first. Use an individual command only for that failed stage. This keeps diagnosis reproducible and avoids creating different local states while debugging.

## V0310 camera regression remains applicable

V0311 does not change ESP firmware or the V0310 production camera transport. If continuing physical camera validation, keep using:

```text
apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino
```

The existing approximately 10–12 FPS production acceptance target at the known-good Wi-Fi position remains a V0310 camera-transport check, separate from V0311 Junction Network acceptance.

V024 / `0_2_4` remains the passed baseline until explicit owner acceptance. Physical/public-road traffic-control authority remains out of scope.
