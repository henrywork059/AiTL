# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_2_0` — capture deletion, camera-aligned zones, Live AI zone overlays, and compact signal display

## Implemented prototype functions

- receive or simulate camera frames
- use a controllable synthetic traffic scene with top-to-bottom pedestrians and horizontal vehicle motion
- choose light / normal / busy simulation density and pause/resume an inspection frame
- capture and persist dataset images
- delete unwanted captures together with paired metadata and saved manual labels
- manually label frames in the app
- build a managed YOLO dataset
- run local Ultralytics YOLO training
- monitor per-epoch validation fitness / mAP convergence
- stop training automatically when validation fitness stops improving for the configured patience window
- discover, choose, default, and delete local trained models
- run live inference overlays on receiver/simulation frames
- create, edit, persist, and reset traffic-zone polygons directly over the current camera/simulation feed
- overlay saved zones on Live AI with reference-to-frame scaling
- show the simulation-only traffic phase as a compact signal at the top-right of Live AI
- count live detection centres inside configured zones
- generate auditable simulation-only traffic phase recommendations from zone counts
- persist active runtime settings
- inspect real recent backend logs with request/error metadata
- keep long model IDs and paths contained inside the Live AI model panel

## Safety scope

This project is for prototype, classroom, and simulation use only. Zone-aware traffic recommendations and live AI detections are not connected to real public-road traffic infrastructure.
