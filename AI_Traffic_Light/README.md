# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_1_6` — Live AI layout containment and controllable simulation scene

## Implemented prototype functions

- receive or simulate camera frames
- use a synthetic traffic scene with top-to-bottom pedestrians and horizontal vehicle motion
- choose light / normal / busy simulation density and pause/resume an inspection frame
- capture and persist dataset images
- manually label frames in the app
- build a managed YOLO dataset
- run optional local YOLO training
- discover, choose, default, and delete local trained models
- run live inference overlays on receiver/simulation frames
- keep long model IDs and paths contained inside the Live AI model panel

## Safety scope

This project is for prototype, classroom, and simulation use only. Live AI detections do not directly control real public-road traffic infrastructure.
