# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_1_7` — training convergence, automatic early stopping, and working prototype tools

## Implemented prototype functions

- receive or simulate camera frames
- use a controllable synthetic traffic scene with top-to-bottom pedestrians and horizontal vehicle motion
- choose light / normal / busy simulation density and pause/resume an inspection frame
- capture and persist dataset images
- manually label frames in the app
- build a managed YOLO dataset
- run local Ultralytics YOLO training
- monitor per-epoch validation fitness / mAP convergence
- stop training automatically when validation fitness stops improving for the configured patience window
- discover, choose, default, and delete local trained models
- run live inference overlays on receiver/simulation frames
- create, edit, persist, and reset traffic-zone polygons
- count live detection centres inside configured zones
- generate auditable simulation-only traffic phase recommendations from zone counts
- persist active runtime settings
- inspect real recent backend logs with request/error metadata
- keep long model IDs and paths contained inside the Live AI model panel

## Safety scope

This project is for prototype, classroom, and simulation use only. Zone-aware traffic recommendations and live AI detections are not connected to real public-road traffic infrastructure.
