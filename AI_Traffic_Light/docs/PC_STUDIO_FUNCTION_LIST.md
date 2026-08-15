# PC Studio Function List (implemented highlights)

## Camera
- receive JPEG/PNG frame
- simulation mode
- latest-frame preview
- Light / Normal / Busy synthetic density
- pause/resume synthetic scene

## Dataset
- capture latest frame with metadata
- manual bounding-box labeling
- managed YOLO dataset build

## Training
- local Ultralytics training
- per-epoch validation fitness / mAP convergence history
- live training convergence plot
- configurable patience-based automatic early stopping

## Inference / Models
- discover local trained models
- choose a model to load
- set a default model for auto-load
- delete an outdated model run
- run live detections on receiver/simulation frames
- adjust backend confidence down to 1%
- toggle overlay boxes and labels
- filter visible classes

## Zones / Traffic simulation
- edit and persist polygon zones
- reset simulation-aligned reference zones
- count live detection centres inside zones
- generate simulation-only phase recommendations with reasons and frame/zone audit data

## System
- persist runtime confidence, camera-status polling, training patience, and log level
- inspect real recent backend logs with request IDs/error codes when available

## Still later
- automatic labeling
- model export/runtime package
- physical public-road traffic control
