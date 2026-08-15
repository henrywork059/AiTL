# PC Studio Function List (implemented highlights)

## Camera
- receive JPEG/PNG frame
- simulation mode
- latest-frame preview
- Light / Normal / Busy synthetic density
- pause/resume synthetic scene

## Dataset
- capture latest frame with metadata
- delete a captured image together with metadata and saved manual labels
- manual bounding-box labeling
- managed YOLO dataset build

## Training
- local Ultralytics training
- per-epoch validation fitness / mAP convergence history
- live training convergence plot
- configurable patience-based automatic early stopping

## Inference / Models
- discover/load/default/delete trained models
- run live detections on receiver/simulation frames
- adjust backend confidence down to 1%
- toggle detection boxes, labels, classes, and saved zone overlays

## Zones / Traffic simulation
- edit and persist polygons directly over the current camera/simulation feed
- reset simulation-aligned reference zones
- scale persisted zones onto Live AI frames
- count live detection centres inside zones
- generate simulation-only phase recommendations with reasons and frame/zone audit data
- show a compact simulation-only traffic signal at the top-right of Live AI

## System / development integrity
- persist runtime confidence, camera-status polling, training patience, and log level
- inspect real recent backend logs with request IDs/error codes when available
- load backend release metadata from root `VERSION` instead of duplicating release strings across runtime endpoints
- reuse one checked frontend project-version constant for Dashboard, navigation, and offline fallback metadata
- validate repository/version surfaces with `scripts/check_structure.py`
- validate patch ZIP path/exclusion/integrity rules with `scripts/validate_patch_zip.py`
- provide explicit AI-agent workflow/checklist documentation for candidate gating, testing evidence, and runtime-data preservation

## Still later
- automatic labeling
- model export/runtime package
- physical public-road traffic control
