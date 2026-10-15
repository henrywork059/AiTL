# Patch 0_5_9 — Global AI Models and Camera AI Preview

**Candidate:** `0_5_9`; **previous:** `0_5_8`; **owner-accepted baseline:** `0_5_0`.

## Changes

- Traffic precedes AI in sidebar; AI Models appears above Camera AI Preview; Settings navigation and route removed while existing backend runtime settings are preserved.
- AI Models supports upload of unique Ultralytics-compatible `.pt` weights into the existing model registry, model selection/load/default/unload, rejection of deleting an active model, and saved global detection confidence and inference interval using a 100–2000 ms slider.
- `MultiCameraInferenceService` runs one shared loaded YOLO model against the latest available frames of all saved streaming ESP and simulated cameras. One worker processes frames sequentially, maintains per-camera results, never queues stale frames, and suppresses stale displayed results; model switch clears previous results when processed. The requested interval is best-effort.
- Camera AI Preview selects a registered camera without mutating application source selection, displays actual per-camera frames and detected boxes/labels/confidence, overlays existing Crosswalk Side A/B region geometry and shows per-class per-region current counts in a separate table. Region counting uses one bottom-center ground point and assigns an object to the first containing region if regions overlap.
- Existing legacy selected-source inference/tracking/traffic, Network overview, dataset capture, signal-control safety and firmware remain unchanged. No cross-camera identity matching, multi-junction live policy fusion or certified physical control is claimed.

## API

- `POST /api/models/upload?model_id=<id>` raw bytes, max 200 MiB, no replacement.
- `GET /api/inference/cameras/{source_id}` latest cached per-camera background AI result.
- `GET /api/camera/preview/{source_id}` fresh selected saved camera image without changing app source.
- `PUT /api/settings/runtime` adds optional `inference_interval_ms` while preserving previous fields and old saved file compatibility.

## Test and acceptance

New focused `scripts/test_v059_global_ai.py` and updated V058 UI-wiring regression. Run full Windows `scripts/update_test_run.ps1`, including Python, structure, frontend build, smoke and multi-camera visual/hardware validation. These checks and owner PASS remain pending. Accepted baseline is still `0_5_0`.
