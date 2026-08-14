# Changelog

## 0_1_5 — Model selection, deletion, and live-visibility controls

- Reviewed the trained-model loading path and replaced the latest-only UX with explicit model selection from discovered local `outputs/training/*/weights/best.pt` runs.
- Added backend model-registry functions to list local trained models, persist a default model selection, and delete an outdated model run directory.
- Added a default-model metadata file under `outputs/training/` so Live AI can auto-load the chosen default model after restart.
- Added inference API support for loading a selected/default model instead of only the newest model.
- Extended live detections so the frontend confidence slider is sent to the backend and can go down to 1% for diagnosis.
- Added live visibility controls to show/hide boxes, show/hide labels, and filter visible classes without changing the underlying source frame.
- Implemented a working Model Registry page in the frontend with refresh, load, set-default, and delete actions.
- Updated documentation, error codes, smoke coverage, and local acceptance checks for V015.
- Live detections still do not control zones or traffic signals; automatic labeling, model export, and physical public-road control remain disabled.

## 0_1_4 — Trained-model live inference overlay

- Replaced the inference placeholder with a real Ultralytics-backed service that discovers local `outputs/training/*/weights/best.pt` files and loads the newest run.
- Added model status, load-latest, unload, live-detection, and exact inferred-source-frame endpoints using the existing API envelope/request-ID conventions.
- Runs the loaded trained model on the newest receiver or simulation frame and returns class, confidence, and original-image `xyxy` coordinates.
- Caches inference per camera frame so repeated frontend polls do not rerun the same frame.
- Keeps the exact source image used for each detection result so frontend overlays stay aligned even while simulation frames continue moving.
- Upgraded Live AI to automatically load the newest trained model when available, show the real camera/simulation image, overlay boxes, filter displayed confidence, and show inference latency/model state.
- Preserved the original mock Live AI scene as a fallback when no camera frame exists.
- Added trained-model inference service tests, smoke coverage, API documentation, and V014 acceptance checks.
- Live detections do not yet feed zone counts or traffic-light decisions; automatic labeling, model export, and physical public-road control remain disabled.

## 0_1_3 — Manual labeling and managed YOLO dataset

- Replaced the Dataset Review placeholder with a working captured-frame browser and manual bounding-box label editor.
- Reused the shared six-class schema: person, car, bus, truck, motorcycle, and bicycle.
- Added persistent label JSON files under each capture session without altering the original image or capture metadata.
- Treats a saved zero-box review as a valid negative example and keeps unreviewed captures distinct.
- Excludes captures tagged `bad` from managed training builds.
- Added a deterministic managed YOLO train/validation builder at `datasets/yolo/` with image copies, normalized `.txt` labels, `data.yaml`, and a manifest.
- Requires at least two reviewed non-bad frames so train and validation sets are distinct.
- Detects label changes after a dataset build and marks the managed dataset stale until rebuilt.
- Connected the existing Train / Export page to the managed `yolo/data.yaml` status while preserving support for other labeled YOLO YAML files inside `datasets/`.
- Added labeling/build API contracts, stable dataset error codes, service tests, and acceptance documentation.
- Automatic labeling, live YOLO inference, model export, and physical public-road traffic-light control remain disabled.

## 0_1_2 — Persistent capture and optional labeled-dataset training

- Replaced the Dataset Capture placeholder with a working receiver/simulation capture page.
- Added atomic image and paired JSON metadata writes under `datasets/captures/<session>/`.
- Changed synthetic simulation frames to PNG so they can be saved by the same capture path as device images.
- Added persistent capture counts, session IDs, quality tags, notes, stable envelopes, and request IDs.
- Added a real optional Ultralytics YOLO background runner with dataset-path/config validation and status polling.
- Added frontend capture/training controls, strict mutation error handling, tests, and generated-data ignores.
- Raw captures remain unlabeled; real detection training requires a prepared YOLO dataset and the optional training dependency.
- Real inference, automatic labeling, model export, and physical traffic-light control remain disabled.

## 0_1_1 — Camera frame receiver and simulation

- Added an in-memory PC-side endpoint for ESP32/Raspberry Pi JPEG or PNG frame uploads.
- Added latest-frame metadata, stale-frame detection, and an image response endpoint.
- Replaced the Camera Sources placeholder with an automatically refreshing preview and receiver status.
- Added a moving synthetic camera mode that tests the same viewer path without camera hardware.
- Added stable camera validation errors and documented the upload contract.
- Updated Windows backend launchers to listen on the local network for future camera-node uploads.
- Real AI inference, training, and physical traffic-light control remain disabled.

## 0_1_0 — PC Studio test-ready mock version

- Promoted the PC Studio template from layout-only to a local smoke-testable mock version.
- Added backend smoke-test endpoints and backend self-check script.
- Added frontend/backend status display, refresh flow, and mock API integration checks.
- Updated visible version labels from 0_0_4 to 0_1_0.
- Added human testing instructions and a test-ready checklist.
- Still intentionally excludes real YOLO inference, real camera capture, training, model export, and physical traffic-light control.

## 0_0_4 — PC Studio app template and function map

- Added the first structured PC Studio frontend template.
- Added sidebar navigation and placeholder pages for all planned main functions.
- Added reusable layout, placeholder, metric, checklist, and status components.
- Added central frontend page and function registries.
- Added backend placeholder route modules for camera, inference, zones, dataset, training, model registry, settings, logs, and template metadata.
- Updated backend app wiring to expose the placeholder API structure.
- Expanded error-code ranges for future camera, inference, zone, dataset, training, model, settings, and logging work.
- Added human/AI documentation for confirming the PC Studio function list and GUI layout before real implementation.

## 0_0_3 — Modular code, API contracts, logging, and error codes

- Added coding standards for small, debuggable modules.
- Added backend logging/error-code infrastructure.
- Added API response envelope helpers and exception handling.
- Added frontend API/debug logging helpers.
- Refactored placeholder backend routes into smaller route/core/service modules.
- Added documentation for API contracts, debugging, logging, and error-code ranges.
- Added patch notes for **0_0_3**.

## 0_0_2 — Human and AI-agent instruction docs

- Added root-level `AGENTS.md` for AI agents and coding assistants.
- Added `docs/AI_AGENT_GUIDE.md` with detailed project rules for AI agents.
- Added `docs/HUMAN_GUIDE.md` with human-facing usage, upload, patch, and safety instructions.
- Updated README documentation links.
- Updated version metadata to **0_0_2**.

## 0_0_1 — Documentation and version cleanup

- Corrected project wording from the earlier “Version 1 / 0.1.0” draft to the chosen **0_0_x** versioning scheme.
- Updated README layout references from `AI_Traffic_Light_v1/` to `AI_Traffic_Light/`.
- Added clear baseline/patch distinction:
  - `0_0_0` = initial skeleton.
  - `0_0_1` = documentation/version cleanup.
- Updated documentation roadmap and versioning notes.
- Updated placeholder UI/backend version labels to avoid old version naming.

## 0_0_0 — Initial starter skeleton

- Added monorepo project structure.
- Added PC Studio backend placeholder.
- Added PC Studio frontend placeholder GUI.
- Added ESP32-CAM firmware placeholder.
- Added shared schemas.
- Added documentation and roadmap.
- Added sample fake detection data.
- Added Windows helper scripts.
