# V0571 — Isolated SUMO lane queues and turning scenarios

Candidate `0_5_71`; previous `0_5_70`; accepted baseline `0_5_0`; Update 26 / S04. Owner PASS pending.

## Implementation

The trusted synthetic SUMO scenario is internally opt-in via `GeneratedSession(seed, lane_scenario=True)`; the standard shadow session and legacy authoritative simulator remain unchanged. The isolated libsumo worker uses the existing validated topology and protected phase upper bound. Seeded finite demand includes straight, left/right turns, a temporary downstream blocker and pedestrians. Lane-leader admission grants at most one vehicle link, rejects insufficient exit space, holds vehicle entry while a pedestrian or vehicle occupies the junction, and allows pedestrian entry only during pedestrian green with no vehicle inside. Yellow, flashing and all-red grant no new entry. No new network listener, frontend mode, API schema, dependency or physical output. Native SUMO retains lane following and motion ownership; the admission function is not an independent physical safety controller.

## Verified evidence

Application/test revision `b850a2a9077a96cbc4cfcd5931d5244eb84ac57b`: [standard CI 45764874498](https://github.com/henrywork059/AiTL/actions/runs/45764874498) and [native SUMO CI 45764874374](https://github.com/henrywork059/AiTL/actions/runs/45764874374) passed. Actual native JSON printed in job logs; evidence artifact [15091029072](https://github.com/henrywork059/AiTL/actions/runs/45764874374/artifacts/15091029072). Two runs, seed 42, each 440 s at 0.2 s steps (2200 steps); identical SHA-256 digest b5f4f58b81dad25f06447517a09062968c1c3fcebfe82d160d5242b6080946f7 and metrics. Per run: 626 stopped-queue ticks (at least two stopped west-approach vehicles), 577 ticks with a stopped vehicle within 8 m of the lane endpoint, 116 blocked-exit checks during vehicle green, 16 observed authorized vehicle entry transitions, 8 authorized pedestrian crossing-edge entry transitions, 21 pedestrian CLEAR continuation occupancy samples (per-person samples, not necessarily distinct ticks), 116 pedestrian crossing-occupancy ticks, both turn exits CN/CS observed, 17/17 vehicle arrivals including the exit blocker and 4/4 person arrivals. Admission, seeded demand, protected permissions, actual entry transitions and prior shadow lifecycle checks passed; standard compile, structure, offline regressions, frontend data-access tests, typecheck, build and blocking npm audit passed. Evidence is executed synthetic simulation, not field data. Exact release commit CI pending at publication.

## Owner acceptance

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic simulation only. Confirm default legacy view, optional Three.js preview, existing pause/reset, camera A–D, and editor vertex drag/save/reopen; verify no change in coordinates or physical outputs. Do not expect turning traffic in the default view. Optional native evaluation requires the pinned Windows wheels and the existing SUMO evaluation workflow; run `.github/scripts/sumo_lane_trial.py` with an output JSON path only in the trusted isolated environment. Owner alone confirms PASS.

## Limitations and next update

Single generated junction, restricted route set and conservative single vehicle-link grant are not a calibrated traffic model, collision certification, live controller comparison or throughput improvement. Capacity check uses observed exit rear-bumper space, not a general network reservation/spillback algorithm; occupancy is sampled at 0.2 s. The earlier controlled fixture reported emergency braking warnings; native fidelity, resource and endurance checks remain outstanding. Normal camera simulation and editor are unchanged; no fresh manual Windows drag/save or physical ESP acceptance. Lane scenario is an internal evaluation seam, not a new UI feature. Default engine migration is reserved for Update 28 after parity/resource gates. No public-road actuation. 26/39 candidates delivered (66.7%); next Update 27 / S04.
