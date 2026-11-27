# V0572 — Isolated SUMO two-junction corridor and spillback

Candidate `0_5_72`; previous `0_5_71`; accepted baseline `0_5_0`; Update 27 / S04. Owner PASS pending.

## Implementation

The optional `CorridorSession(seed)` generates a trusted two-junction SUMO fixture with centres 45 m apart and directed vehicle route WA → AB → BE. It reuses the pinned native child process, lane-leader exit-space admission and validated per-junction phase mapping. SUMO owns continuous vehicle motion and persistent IDs. `set_junction_phases` requires explicit virtual phases for both A and B; independently validated permissions, internal vehicle occupancy and pedestrian crossing occupancy restrict each junction. The downstream exit-space gate prevents upstream admission during observed spillback. No new dependency, saved topology integration, HTTP endpoint, frontend selection, physical output or live signal authority; standard shadow and legacy defaults remain unchanged.

## Verified evidence

Application revision `807864fafaf14eab75721cebddb542943635c774`: [standard CI 45765997190](https://github.com/henrywork059/AiTL/actions/runs/45765997190) and [native SUMO CI 45765997178](https://github.com/henrywork059/AiTL/actions/runs/45765997178) passed. Native JSON inspected in job logs; [artifact 15091264465](https://github.com/henrywork059/AiTL/actions/runs/45765997178/artifacts/15091264465). Seed 42, two 800 s runs, step 0.2 s (4000 steps/run); identical SHA-256 digest d539ea50feb3d0501a7d638d6d04d82e297bc6e4dd0eca6b2ef41b48695a3d63 and all metrics. Per run all 16 distinct vehicle IDs observed entering and leaving AB then arriving; no duplicate snapshot IDs or active/arrived overlap, all 4 pedestrians arrived. Peak observed AB occupancy 4 vehicles; 324 blocked-admission checks with stopped upstream demand and connector front-bumper position below 12 m, of which 207 occurred during downstream all-red. 75 ticks with simultaneous nonempty grants and different requested phases; 4 authorized pedestrian crossing entries and 13 per-person CLEAR occupancy samples. Link travel time is measured from first sampled AB entry to first sampled internal B entry and includes waiting, not door-to-door journey time. Per-ID seconds: v0 109.8, v1 134.0, v2 133.6, v3 111.6, v4 29.0, v5 13.2, v6 13.4, v7 13.2, v8 11.8, v9 13.2, v10 13.4, v11 13.2, v12 12.0, v13 13.2, v14 13.2, v15 13.0. Offline corridor admission, prior native trials, lifecycle and mapping checks, standard compile, structure, offline regressions, frontend tests/typecheck/build and blocking audit passed. Executed synthetic simulation, not field evidence. Exact release commit CI pending at publication.

## Owner acceptance

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic simulation only; verify unchanged legacy default, optional Three.js view, pause/reset, camera A–D, editor vertex drag/save/reopen and no physical outputs. Corridor experiment is not visible in the default UI. Optional native validation uses the pinned Windows SUMO evaluation workflow or `.github/scripts/sumo_corridor_trial.py` with an output JSON path in the trusted isolated environment. Owner alone confirms PASS.

## Limitations and next update

Restricted eastbound route and explicit phase schedules (B initially all-red for 120 s) deliberately generate congestion; no optimized cooperation, arbitrary configured topology, calibrated demand, general network capacity guarantee, collision certification or superiority claim. The observed peak occupancy is not a universal capacity limit. Sampling at 0.2 s cannot establish continuous-time physical safety. Earlier single-junction controlled fixture still reported emergency-braking warnings. Existing benchmark and normal camera simulation/editor remain unchanged; no new browser or owner Windows/ESP acceptance. Default migration (Update 28) requires separate parity, resource and rollback evidence; do not switch prematurely. No public-road actuation. 27/39 candidates delivered (69.2%); next Update 28 / S04.
