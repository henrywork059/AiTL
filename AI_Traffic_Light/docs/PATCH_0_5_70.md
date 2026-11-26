# V0570 — Persistent articulated pedestrians and observed gait

Candidate `0_5_70`; previous `0_5_69`; accepted baseline `0_5_0`; Update 25 / S03. Owner PASS pending.

## Implementation

The optional Three.js preview replaces pedestrian box proxies with persistent volumetric figures (head, torso, separate arms, legs, shoes). PedestrianMotion follows canonical observed positions, bounds interpolation to 450 ms, derives gait from observed displacement, stops gait when stationary/paused, and resets on backwards/large jumps, source/density/clock changes or gaps. RoadRenderer retains mesh groups by existing pedestrian slot ID and color; removes absent groups and disposes owned materials. Shared geometry, mirrored heading, curb elevation and existing animation scheduling are retained. No extrapolation, new crossing authorization, simulator speed or controller change. Legacy CSS remains default and retains the source-coordinate editor and overlays. No API, dependency or physical-output changes.

## Verified evidence

Application revision `40fcd2ea232ae4a79d16ca17d1b7a16e15cf510c`: [standard CI 45755422048](https://github.com/henrywork059/AiTL/actions/runs/45755422048) and [renderer CI 45755422084](https://github.com/henrywork059/AiTL/actions/runs/45755422084) passed. Standard CI executed three Python lifecycle tests on the actual existing movement helper with fixed phase inputs: both directions, WALK entry, CLEAR continuation, non-WALK curb holds, 30 vs 90 reference pixels/s slow/normal fixtures and seeded reentry. TypeScript motion tests passed for stationary/slow displacement, repeated frames, pause/resume, reentry both directions, reset/source/density/gap and removal; sample independence also asserted. Actual WebGL trial directly asserts persistent pedestrian group reference identity, interpolated position, limb rotation, paused gait freeze and removal; drawing, top view, context loss and cleanup passed. React integration confirms opt-in, source change, editor/overlay fallback, retry and rollback. Both blocking audits reported zero known npm vulnerabilities at execution time. Downloaded [artifact 15087790604](https://github.com/henrywork059/AiTL/actions/runs/45755422084/artifacts/15087790604); SHA-256 31048dfc19e162a4076c5031a3c1f74901f73dd67bba2a91ad2572f953358f35 matches metadata; 1000×650 actual screenshot inspected, three figures (two pavements, one crossing), four vehicles, markings and signals visible, MESH_RENDERER_PASS. Screenshot is a deliberately staged rendering fixture, not proof of safe concurrent movements. Package/lock blobs match b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence: executed synthetic tests, not field data.

## Owner acceptance

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic simulation only. Confirm legacy default, hide visible overlays if necessary, select Three.js preview; observe pedestrian approach, waiting, WALK/CLEAR, direction, pause/resume and reentry across A–D; test orbit/Top/Zoom/Reset and resize. Confirm no walking in place after observations settle. Select Legacy view, open editor, drag/save/reopen vertex and verify unchanged reference coordinates; re-enable overlays to verify fallback. Confirm no physical camera/signal output changes. Owner alone confirms PASS.

## Limitations and next update

Backend pedestrian IDs are recycled slots, not persistent trip identities; reentry snaps rather than traverses the scene. Gait is an illustrative distance-derived animation, not a biomechanical model or accessibility classification. Slow fixture tests do not establish full clearance safety. Non-WALK holds test signal-blocked entry only, not physical obstructions/collision avoidance or downstream capacity. The legacy movement helper is unchanged; renderer may trail observations or snap on reset/pause and is not a safety authority. Small low-poly figures, viewport footprint and Vite large-chunk warning remain. Full Windows owner visual/coordinate drag-save acceptance, native GPU performance, endurance and hardware checks pending. No public-road actuation. Exact release commit CI pending at publication. 25/39 candidates delivered (64.1%); next Update 26 / S04.
