# PC Studio Backend — V017 candidate

FastAPI backend for the local AI Traffic Light prototype.

## Working prototype functions

- receive device JPEG/PNG frames and run the controllable synthetic camera;
- persist captures, manual labels, and managed YOLO datasets;
- run optional local Ultralytics training with per-epoch convergence history and automatic early stopping;
- discover, load, default, and delete trained `best.pt` models;
- run trained-model inference on receiver/simulation frames;
- persist editable traffic zones and count live detection centres inside them;
- return simulation-only traffic recommendations from current zone counts;
- persist runtime confidence/polling/patience/log-level settings;
- expose recent real backend log records with request IDs where available.

Local datasets, runtime settings/zones, and trained models remain runtime data. Trained models stay under `outputs/training/` and are not part of code patches.

This backend is for prototype, simulation, classroom, and supervised testing only. It is not a public-road traffic controller.
