# Patch 0_1_7 — Training convergence, automatic early stopping, and real prototype tools

## Purpose

V017 builds on V016 without replacing the working capture/training/inference/model-management architecture. It adds observable training convergence and automatic early stopping, then converts the remaining PC Studio mock/template pages into working prototype surfaces.

## Training convergence and early stopping

- Training requests now include `patience` (1-100).
- The training service passes `patience` directly to local Ultralytics training.
- `on_fit_epoch_end` captures validation-aware metric history after each train+validation epoch.
- Status exposes validation fitness, best fitness, mAP50-95, mAP50, available train/validation loss totals, best epoch, and epochs without improvement.
- The frontend renders fitness and mAP50-95 as a live SVG convergence plot.
- If Ultralytics returns before the requested maximum epoch count, the run is reported as `early_stopped`; best model discovery remains unchanged.

## Working prototype pages

- **Dashboard:** current version is derived from backend/smoke state instead of stale hard-coded V015 text.
- **Zone Editor:** editable polygon canvas, validation, persistent `config/zones.json`, and reset-to-reference controls.
- Runtime `config/zones.json` and `config/runtime_settings.json` are ignored by `config/.gitignore` so local choices do not pollute source-control status.
- **Traffic Logic:** live trained-model detections are mapped into persisted zones using detection-box centres and produce a simulation-only recommendation with an auditable reason.
- **Settings:** persistent confidence, Live AI camera-status polling, training patience, and backend log level.
- **Logs:** bounded real backend log records with timestamp, level, scope, request ID, and error code when present.

## Architecture

- FastAPI routes remain thin.
- Training, zones, traffic evaluation, settings persistence, and log buffering live in backend services/core modules.
- New request schemas are in `app/models.py`.
- Existing API envelopes/request IDs and stable error codes are reused.
- Frontend API access remains in the existing API module; the convergence chart is a small reusable component.

## Safety

Zone-aware traffic results are **simulation-only recommendations** for prototype/classroom testing. V017 does not connect live detections or decisions to physical traffic lights or public-road infrastructure.

## Remaining limitations

- Automatic labeling is not implemented.
- Model export/runtime packaging is not implemented.
- Device-camera firmware remains outside this PC Studio patch.
- Zone counting uses detection-box centres; tracking, dwell time, trajectory prediction, and safety certification are not implemented.
- Convergence is observed through Ultralytics validation fitness and its built-in patience behavior; the plot is diagnostic and does not add a second custom stopping algorithm.
