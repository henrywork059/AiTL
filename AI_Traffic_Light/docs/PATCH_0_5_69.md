# V0569 — Persistent vehicle meshes and bounded motion interpolation

Candidate `0_5_69`; previous `0_5_68`; accepted baseline `0_5_0`; Update 24 / S03. Owner PASS pending.

## Implementation

The opt-in Three.js preview uses distinct procedural car, SUV, van and bus meshes with body/cabin proportions, windows, wheels and lights. RoadRenderer retains mesh groups by backend vehicle slot ID and shape signature; removes absent groups and disposes owned materials. VehicleMotion interpolates authoritative observed centers and shortest-angle headings for at most 450 ms, without extrapolation or simulator-clock mutation. Large jumps, backwards straight movement, changed shape, source/density change, clock rollback or a gap over one simulation second reset the affected motion; pause/resume snaps to the authoritative pose. RequestAnimationFrame runs only during active interpolation. The legacy CSS renderer remains default and preserves editing/overlay fallback, camera coordinates and all backend APIs and signal authority. No dependency or physical output changes.

## Verified evidence

Application revision `8abcac5e874f488604bf084983fbe6976f8159d0`: [standard CI 45753991244](https://github.com/henrywork059/AiTL/actions/runs/45753991244) and [renderer CI 45753991208](https://github.com/henrywork059/AiTL/actions/runs/45753991208) passed. Actual deterministic motion regression covers midpoint/end, interrupted interpolation, duplicate snapshot, synthetic turning and mirrors, east/west reentry, pause/resume, reset, density/source change, removal and frame-sampling independence. Browser trial checks four mesh variants, increasing heights, bus detail and shape signature; actual WebGL drawing, pixel variation, top view, context-loss, repeated disposal, and production React editor/overlay fallback, source switch, retry/rollback and cleanup passed. Persistent group reuse/removal verified by source inspection; the browser test does not directly assert group reference identity across updates. Both blocking npm audits reported zero known vulnerabilities at execution time. Downloaded [artifact 15086527983](https://github.com/henrywork059/AiTL/actions/runs/45753991208/artifacts/15086527983); archive SHA-256 f9211ce575f67c11158eb610d188ee899076c7319293fe0aa3b59a802983e110 matched metadata. Actual 1000×650 screenshot visually inspected: four distinguishable orange vehicles, crossing, markings and signals, MESH_RENDERER_PASS. Package and lock blob hashes match prior validated manifests b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence class: executed synthetic fixtures and browser trials; not field data.

## Owner acceptance

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use the synthetic preview, confirm legacy default, disable visible overlays if needed, select Three.js preview; observe all vehicle classes, both travel directions, stop/reentry, pause/resume and density changes. Switch camera A–D, orbit/Top/Zoom/Reset and resize. Select Legacy view; open the editor, drag/save/reopen a vertex and check unchanged coordinates; enable overlays and verify automatic fallback. Confirm no physical camera or signal output changes. Owner alone confirms PASS.

## Limitations and next update

Existing backend IDs are recycled slots, not unique trip IDs; large-jump and direction-based respawn detection is heuristic. Straight-road backend does not execute turning paths; turning tests are synthetic. Interpolation intentionally trails observations, may snap on pause/reset or stale gap, and does not measure controller timing or safety. Direct live mesh-object identity assertion, real Windows owner drag/save round trip, native GPU benchmarks, endurance, full-motion visual acceptance and hardware checks remain outstanding. Models are low-poly; viewport footprint and Vite large-chunk warning remain. Pedestrians remain coarse until Update 25. No public-road actuation. Exact release commit CI pending at publication. 24/39 candidates delivered (61.5%); next Update 25 / S03.
