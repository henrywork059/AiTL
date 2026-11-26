# V0568 — Opt-in Three.js road renderer

Candidate `0_5_68`; previous `0_5_67`; accepted baseline `0_5_0`; Update 23 / S03. Owner PASS pending.

## Implementation

Three.js 0.187.0 (MIT, exact pin) renders canonical 1280×720 synthetic road geometry, crossing, markings, pavements/kerbs, virtual signals and coarse agent proxies. SimulationCamera3D retains polling, camera controls and source matching; ThreeRoadView owns WebGL lifecycle and RoadRenderer is shared with the trial. Default CSS rendering is retained; select Three.js preview explicitly for compatible snapshots without visible region/detection overlays. Editor/overlay modes, incompatible or absent snapshots and WebGL failures fall back to legacy. Retry or select Legacy view. No API, coordinate, simulator/controller authority or physical output changes.

## Verified evidence

Application revision `6380561a6038d0dc3ee85a4bd7cf2bd1a0dc705f`: [standard CI 45740124107](https://github.com/henrywork059/AiTL/actions/runs/45740124107) and [renderer CI 45740124021](https://github.com/henrywork059/AiTL/actions/runs/45740124021) passed. Geometry fixtures cover four mirrored views; isolated WebGL draw/pixel/top-view/context-loss/disposal and React integration tests passed (actual component with mocked read-only synthetic scene: default legacy, opt-in, source A→B, top view, editor/region-overlay fallback, loss/retry, rollback and cleanup). Both audits reported zero known npm vulnerabilities at execution time. Exact generated manifest and lock blobs b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b; eight new lock entries, existing non-root entries unchanged. Earlier 23c screenshot inspected; [23d artifact 15080298917](https://github.com/henrywork059/AiTL/actions/runs/45740124021/artifacts/15080298917) retains screenshot/manifests; no fresh manual inspection claimed. Evidence: executed synthetic browser tests, not field data.

## Owner acceptance

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic preview; confirm legacy default, hide visible overlays if necessary, select Three.js preview, test orbit/Top/Zoom/Reset, A–D and resize; select Legacy view, reopen the editor, drag/save/reopen a vertex, check unchanged reference coordinates, re-enable overlays and verify fallback. Confirm physical camera and signal output unchanged. Owner alone confirms PASS.

## Limitations and next update

Coarse agents, snapshot stepping, relatively small road footprint, uncalibrated projection and Vite large-chunk warning remain. Detailed vehicle/pedestrian models and interpolation are Updates 24/25. Editor DOM fallback is verified; actual vertex drag/save round trip, full Windows/ESP owner acceptance, native GPU performance, resize stress and matched benchmarks remain pending. No public-road actuation or hardware certification. Exact release commit CI pending at publication. 23/39 candidates delivered (59.0%); next Update 24 / S03.

See [integration evidence](S03_RENDERER_INTEGRATION.md).
