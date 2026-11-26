# Simulator migration readiness — Update 28 / S04

Current candidate 0_5_72; accepted baseline 0_5_0. Target 0_5_73 only when justified. Exact previous release CI [45766563112](https://github.com/henrywork059/AiTL/actions/runs/45766563112) passed.

## Gate audit (28a)

The authoritative CameraFrameService still uses LegacySimulationAdapter, pixel agents, a 1280 × 720 crosswalk canvas, four flipped source images, fixed slot IDs, density presets and signal-aware movement. ShadowRuntime receives committed phase observations in 200 ms batches and publishes separate metre-coordinate finite-demand snapshots; it is disabled unless MESH_SUMO_SHADOW=1. The native corridor has separate fixed geometry and no camera or saved-topology projection. Enabling shadow is not an engine migration. Never publish a shadow observation as an authoritative detection, frame or policy input.

| Gate | Current state |
| --- | --- |
| Legacy application/API regressions | Existing standard CI passed on 0_5_72; rerun on 28a |
| Actual shadow noninterference / resource overhead | Passed on 28a; measured shadow overhead only |
| Four views, canonical PNG/capture and zone persistence | Passed on 28a; legacy output only |
| Protected controller phases | Passed on 28a; actual isolated controller and native permission regressions |
| Browser renderer and existing fallback | Passed on 28a; not replacement integration |
| SUMO canonical projection and lifecycle parity | BLOCKED — no replacement publisher; geometry, demand, slow agents, ID semantics and clocks differ |
| Experiment export parity | BLOCKED — existing isolated benchmark is not a native replacement export |
| Matched replacement CPU/RAM/GPU budget | BLOCKED — shadow overhead is not replacement workload; owner hardware budget not established |
| Windows owner editor drag/save, rollback and acceptance | BLOCKED — owner manual test outstanding |

The matched trial runs two fresh processes, fixed seed 42, 100 samples every 0.4 simulated seconds, four scene/frame API pairs per sample; actual legacy PNG/scene hash equality, canonical flips, temporary captures and zone persistence, pause/resume, density reset, stop and child reaping. Physical source-manager sync is mocked; the controller uses an isolated temporary fixed configuration. Native shadow steps are awaited and resource samples include the Python parent and native child. CPU deltas, wall duration and working sets are diagnostic only; the runner is not owner hardware, and one repetition per arm is not statistical evidence of general overhead. 28a actual results: identical digest 3ad9f005ed5343d8be1372de487c9989a401730f120b2b0ed6b602f01a51a0b7; 400 pairs/arm, four captures/arm, all five phases; legacy wall 9.3578373 s, CPU 9.515625 s, final working set 82190336 bytes; shadow-on wall 9.4070982 s, CPU 9.53125 s, final combined working set 179486720 bytes, maximum native agents 15. [Standard CI](https://github.com/henrywork059/AiTL/actions/runs/45770136787), [native CI](https://github.com/henrywork059/AiTL/actions/runs/45770136725), [renderer CI](https://github.com/henrywork059/AiTL/actions/runs/45770136727) passed; actual native JSON inspected in logs, renderer smoke and fallback assertions passed. These are one-run shadow overhead observations, not replacement performance.

## Required next work

First define the canonical native projection and supported scenario/density/slow-pedestrian semantics; do not silently map a four-arm metre network onto an unrelated crosswalk scene. Preserve source IDs, frame and capture provenance, original image coordinates, editor overlays, phase authority and rollback. Establish matched demand, native/legacy frame/scene lifecycle, error/failure behavior, experiment export parity, browser and Windows owner acceptance; then establish resource thresholds with measured replacement workloads. Keep legacy default and opt-in diagnostic mode until all gates pass. Do not remove legacy implementation or enable physical signal actuation.

## 28b — isolated native projection foundation

Native lane geometry is parsed from the trusted generated network, with a single isotropic metre-to-1280×720 transform (24 px margin, y inversion) and inverse coordinates for four mirrored views. The isolated projection session reuses the existing native clock and phase admission, publishes explicit synthetic_sumo_projection provenance, generation/tick and stable native IDs, and renders position markers and lane polylines rather than pretending to match legacy vehicle shapes or four-arm geometry. JSON/CSV and PNGs derive from the same snapshot. Pause/reset/close/failure invalidation and child reaping are tested. Native artifact and standard CI pending. This is not a camera API, capture publisher or existing editor/Three.js geometry integration; replacement density, slow agents, matched demand, experiment export schema, actual browser editor and owner resource/rollback gates remain blocked. Keep default legacy.
