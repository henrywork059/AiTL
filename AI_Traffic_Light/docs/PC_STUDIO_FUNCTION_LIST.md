# PC Studio Function List (implemented highlights)

## Camera
- receive JPEG/PNG frame
- simulation mode and latest-frame preview
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
- edit/persist polygons over the current camera/simulation feed
- waiting, crossing, vehicle queue, ignore, and analytics-only counting-region types
- count whole-frame pedestrians and vehicles from detection frames
- count pedestrians/vehicles separately in each configured non-ignore region
- generate simulation-only phase recommendations using the existing decision zones
- show a compact simulation-only traffic signal in Live AI

## Traffic analytics
- record timestamped pedestrian/vehicle occupancy samples while the backend runs
- select whole-frame or named-region time series
- plot occupancy over selectable time windows
- calculate current, average, peak, busiest-region, and phase-change summaries
- export selected history to CSV
- explicitly clear analytics history without touching datasets/models/zones

## System / development integrity
- persist runtime confidence, camera-status polling, training patience, and log level
- inspect real recent backend logs with request IDs/error codes
- load backend release metadata from root `VERSION`
- validate repository/version surfaces and patch ZIP safety
- preserve runtime datasets, models, training outputs, and traffic history outside source patches

## Counting limitation

Current traffic analytics are sampled occupancy counts, not unique passage/throughput counts. Cross-frame tracking is a later feature.

## Still later
- cross-frame object tracking / unique passage counting
- automatic labeling
- model export/runtime package
- physical public-road traffic control
