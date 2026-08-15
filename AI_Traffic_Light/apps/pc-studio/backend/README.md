# PC Studio Backend — V021 candidate

FastAPI backend for the local AI Traffic Light prototype.

## Working prototype functions

- receive device JPEG/PNG frames and run the controllable synthetic camera;
- persist captures, delete unwanted capture image/metadata/label sets, and build manual-label/managed YOLO datasets;
- run optional local Ultralytics training with per-epoch convergence history and automatic early stopping;
- discover, load, default, and delete trained `best.pt` models;
- run trained-model inference on receiver/simulation frames;
- persist editable traffic zones used by the camera-aligned frontend editor and count live detection centres inside them;
- return simulation-only traffic recommendations from current zone counts;
- return whole-frame and per-region pedestrian/vehicle occupancy counts;
- record bounded detection-backed traffic occupancy history under `outputs/traffic_history/`;
- expose history queries, CSV export, peak/average/busiest-region summaries, and explicit history clearing;
- persist runtime confidence/polling/patience/log-level settings;
- expose recent real backend log records with request IDs where available.

## Release metadata

Root `AI_Traffic_Light/VERSION` is the canonical project release state. `app/core/project_version.py` validates and exposes that metadata to FastAPI app metadata, `/health`, smoke status, and template status so those surfaces do not carry independent hard-coded release strings.

If required `VERSION` fields or underscore-formatted version values are invalid, backend startup/import fails clearly rather than silently reporting an inconsistent release.

## Runtime data and safety

Local datasets, traffic-history records, runtime settings/zones, and trained models remain runtime data. Trained models stay under `outputs/training/` and are not part of source patches.

This backend is for prototype, simulation, classroom, and supervised testing only. It is not a public-road traffic controller.
