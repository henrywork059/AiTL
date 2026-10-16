# Patch 0_5_12 — Automatic Camera-to-Crosswalk Controller Observations

**Candidate** `0_5_12` · **Previous** `0_5_11` · **Accepted baseline** `0_5_0`

## Code changes

- Reuses `MultiCameraInferenceService` latest AI results and `CrosswalkSignalService` independent simulated runtimes. New `crosswalk_observations.py` adapter maps registered saved camera IDs to physical Crosswalk region polygons on Side A/B and produces per-class counts.
- Same region in synchronized two views averages counts by class. Single defined view or currently available camera uses its own count with explicit partial coverage. Missing/stale frames and model changes withdraw observation immediately; valid empty detections remain zero.
- Class counts use both simple and `crosswalk_id:region_id` scenario observation keys; existing ranked class-rule engine supports fractional averages. Untyped counting regions never masquerade as known pedestrian crossing, waiting, or queue metrics.
- Adds physical Crosswalk region choices and source-specific adjustment status to Live Signal Adjustments, and region class counts/source coverage to Network cards.
- Real ESP camera detections can drive explicitly labeled virtual-only independent controllers when camera simulation is off. Virtual state is withdrawn when no fresh camera AI remains, and switching controller mode resets its phase runtime. No physical lights are driven.
- Does not alter core signal phase transitions, camera selection, public-road hardware interfaces, legacy global traffic policy, or Network movement conflict coordination.

## Tests and pending acceptance

New `scripts/test_v0512_camera_crosswalk.py` covers crosswalk isolation, same-region averaging, zero, missing/stale and model-switch cases, plus scenario rule integration; `scripts/test_v0512_crosswalk_wiring.py` checks background wiring and UI. Full local Windows Python/TypeScript/Vite, smoke and hardware validations are not available in the GitHub editing environment. Owner must run full repository test runner and confirm PASS. Baseline remains `0_5_0`.
