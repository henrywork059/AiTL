# PC Studio Backend — V022 candidate

FastAPI backend for the local AI Traffic Light prototype.

## Working prototype functions

- receive device JPEG/PNG frames and run the controllable synthetic camera;
- persist captures, delete unwanted capture image/metadata/label sets, and build manual-label/managed YOLO datasets;
- run optional local Ultralytics training with per-epoch convergence history and automatic early stopping;
- discover, load, default, and delete trained `best.pt` models;
- run trained-model inference on receiver/simulation frames and assign frame-deduplicated prototype track IDs;
- generate persistent signal-aware synthetic vehicle/pedestrian motion with stop-line and crosswalk waiting behavior;
- persist editable traffic zones used by the camera-aligned frontend editor and count live detection centres inside them;
- return the active synthetic signal phase plus detection-driven recommendation metadata from current zone counts;
- return whole-frame and per-region pedestrian/vehicle occupancy counts;
- persist two-point counting lines and generate one directional passage event per tracked object/line;
- record tracked polygon-region entry/exit and completed dwell duration, including pedestrian waiting-zone dwell;
- record bounded detection-backed traffic occupancy history under `outputs/traffic_history/`;
- expose occupancy history queries/CSV plus separate flow-event filters, per-minute buckets, CSV export, active-track status, and explicit flow clearing;
- persist runtime confidence/polling/patience/log-level settings;
- expose recent real backend log records with request IDs where available.

## Release metadata

Root `AI_Traffic_Light/VERSION` is the canonical project release state. `app/core/project_version.py` validates and exposes that metadata to FastAPI app metadata, `/health`, smoke status, and template status so those surfaces do not carry independent hard-coded release strings.

If required `VERSION` fields or underscore-formatted version values are invalid, backend startup/import fails clearly rather than silently reporting an inconsistent release.

## Runtime data and safety

Local datasets, occupancy/flow history records, runtime settings/zones, and trained models remain runtime data. Flow events live under `outputs/traffic_flow/` and are not source-patch content. Trained models stay under `outputs/training/` and are not part of source patches.

This backend is for prototype, simulation, classroom, and supervised testing only. It is not a public-road traffic controller.
