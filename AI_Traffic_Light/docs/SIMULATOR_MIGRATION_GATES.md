# Simulator migration readiness — Update 28 / S04

Current candidate 0_5_72; accepted baseline 0_5_0. Target 0_5_73 only when justified. Exact previous release CI [45766563112](https://github.com/henrywork059/AiTL/actions/runs/45766563112) passed.

## Gate audit (28a)

The authoritative CameraFrameService still uses LegacySimulationAdapter, pixel agents, a 1280 × 720 crosswalk canvas, four flipped source images, fixed slot IDs, density presets and signal-aware movement. ShadowRuntime receives committed phase observations in 200 ms batches and publishes separate metre-coordinate finite-demand snapshots; it is disabled unless MESH_SUMO_SHADOW=1. The native corridor has separate fixed geometry and no camera or saved-topology projection. Enabling shadow is not an engine migration. Never publish a shadow observation as an authoritative detection, frame or policy input.

| Gate | Current state |
| --- | --- |
| Legacy application/API regressions | Existing standard CI passed on 0_5_72; rerun on 28a |
| Actual shadow noninterference / resource overhead | New matched native Windows trial pending |
| Four views, canonical PNG/capture and zone persistence | New actual matched trial pending; not replacement parity |
| Protected controller phases | Actual isolated controller in matched trial; native permission regressions rerun |
| Browser renderer and existing fallback | Fresh renderer workflow pending; not replacement integration |
| SUMO canonical projection and lifecycle parity | BLOCKED — no replacement publisher; geometry, demand, slow agents, ID semantics and clocks differ |
| Experiment export parity | BLOCKED — existing isolated benchmark is not a native replacement export |
| Matched replacement CPU/RAM/GPU budget | BLOCKED — shadow overhead is not replacement workload; owner hardware budget not established |
| Windows owner editor drag/save, rollback and acceptance | BLOCKED — owner manual test outstanding |

The matched trial runs two fresh processes, fixed seed 42, 100 samples every 0.4 simulated seconds, four scene/frame API pairs per sample; actual legacy PNG/scene hash equality, canonical flips, temporary captures and zone persistence, pause/resume, density reset, stop and child reaping. Physical source-manager sync is mocked; the controller uses an isolated temporary fixed configuration. Native shadow steps are awaited and resource samples include the Python parent and native child. CPU deltas, wall duration and working sets are diagnostic only; the runner is not owner hardware, and one repetition per arm is not statistical evidence of general overhead. Actual results are pending.

## Required next work

First define the canonical native projection and supported scenario/density/slow-pedestrian semantics; do not silently map a four-arm metre network onto an unrelated crosswalk scene. Preserve source IDs, frame and capture provenance, original image coordinates, editor overlays, phase authority and rollback. Establish matched demand, native/legacy frame/scene lifecycle, error/failure behavior, experiment export parity, browser and Windows owner acceptance; then establish resource thresholds with measured replacement workloads. Keep legacy default and opt-in diagnostic mode until all gates pass. Do not remove legacy implementation or enable physical signal actuation.
