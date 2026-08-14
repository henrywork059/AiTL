# PATCH 0_1_5 — Model selection, deletion, and live-visibility controls

## Scope

V015 builds on V014 and keeps the project within the prototype PC Studio scope.

This patch adds:

1. trained-model selection instead of latest-only loading;
2. deletion of outdated trained-model runs;
3. three additional useful functions:
   - set a default model for Live AI auto-load;
   - lower backend detection confidence to 1% for diagnosis;
   - live visibility controls for showing/hiding boxes, labels, and classes.

## Backend

- Added a model registry service to scan `outputs/training/*/weights/best.pt`.
- Added persistent default-model metadata in `outputs/training/.aitl_model_registry.json`.
- Added model-registry APIs for listing models, setting default, and deleting a model run.
- Added inference loading by selected `model_id` while keeping the V014 latest-model route.
- Added confidence query support on `/api/inference/detections`.

## Frontend

- Live AI now includes a model selector, default marker, load selected button, set-default button, delete button, unload button, and detailed selected-model metadata.
- Model Registry page is now a working page instead of a placeholder.
- Added overlay visibility toggles and class filters.
- Confidence slider now influences backend inference instead of only frontend display filtering.

## Safety / limitations

- Deleting a model removes the whole run folder under `outputs/training/<run_id>/`.
- Model export is still not implemented.
- Detection outputs remain for review only and do not control real traffic signals.
