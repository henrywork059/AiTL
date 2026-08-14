# AI Traffic Light — 0_1_2 Dataset Capture Project

This repository contains an early **AI vision-based adaptive traffic light project**.

The current candidate is **0_1_2**. It receives or simulates camera frames, previews the newest image, and persistently saves selected frames with paired JSON metadata. It also includes an optional real Ultralytics YOLO training runner for separately labeled YOLO datasets.

## Project concept

```text
Camera/video input
→ object detection for pedestrians and vehicles
→ zone-based counting
→ traffic-light decision simulation
→ GUI visualization and dataset capture
```

This is a **prototype and simulation project**. It must not be connected to real public traffic-light infrastructure.

## What 0_1_2 can test

```text
- PC Studio frontend startup
- FastAPI backend startup
- frontend ↔ backend mock API connection
- mock traffic-scene rendering
- mock pedestrian/vehicle detections
- confidence threshold filtering
- mock traffic-light state display
- logs/error-code page layout
- smoke-test endpoint checklist
- raw JPEG/PNG frame upload to the PC
- automatic latest-frame display and stale-frame status
- moving camera simulation without hardware
- manual capture from receiver or simulation mode
- persistent PNG/JPEG image and JSON metadata pairs
- capture sessions, notes, quality tags, and saved-file counts
- optional background YOLO training from a prepared labeled dataset
```

## What 0_1_2 does not implement yet

```text
- ESP32/Raspberry Pi camera firmware
- real webcam capture
- YOLO/object-detection inference
- segmentation
- automatic object labeling or a bounding-box label editor
- training directly from raw unlabeled captures
- bundled training dependency in the normal lightweight backend install
- model export
- physical traffic-light control
```

## Main apps

### 1. PC Studio App

Runs on the computer. Current 0_1_2 status: **dataset capture candidate awaiting owner acceptance**.

Planned responsibilities:

- camera/video source management
- live AI detection view
- traffic-zone setup
- pedestrian/vehicle counting
- rule-based traffic-light simulation
- dataset capture
- dataset review
- optional labeled-dataset training and future model export
- logs and debugging

### 2. Device Camera App

Runs on an ESP32-CAM or similar camera node. Current status: **placeholder only**.

Planned responsibilities:

- capture frames
- send frames to the PC
- expose simple camera status/settings

The device app should not train AI and should not run heavy segmentation/detection models in the first design.

## Quick local test

Start the backend:

```bat
scripts\start_pc_studio_backend_windows.bat
```

Start the frontend in another terminal:

```bat
scripts\start_pc_studio_frontend_windows.bat
```

Then open:

```text
http://localhost:5173
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

Smoke-test endpoint:

```text
http://127.0.0.1:8000/api/smoke/status
```

Optional backend smoke test:

```bat
scripts\test_backend_smoke_windows.bat
```

Generated captures are written to `datasets/captures/<session_id>/images/` with matching records in `metadata/`. The `datasets/` and `outputs/` folders are ignored by Git and should not be uploaded with patches.

For optional real YOLO training, first prepare a labeled dataset YAML under `datasets/`, then install the extra dependency from the backend folder:

```powershell
pip install -r requirements-training.txt
```

## Current version history

```text
0_0_0 = initial skeleton
0_0_1 = documentation/version cleanup
0_0_2 = human and AI-agent docs
0_0_3 = modular code, API, logging, and error-code standards
0_0_4 = PC Studio app template and function map
0_1_0 = first test-ready mock PC Studio version
0_1_1 = camera frame receiver, live preview, and simulation mode
0_1_2 = persistent receiver/simulation capture and optional labeled-dataset training
```

## Important docs

Start here:

```text
docs/START_HERE.md
docs/HUMAN_GUIDE.md
docs/LOCAL_TESTING.md
docs/TEST_READY_CHECKLIST.md
docs/PC_STUDIO_TEMPLATE.md
docs/PC_STUDIO_FUNCTION_LIST.md
docs/PC_STUDIO_GUI_LAYOUT.md
docs/AI_AGENT_GUIDE.md
docs/CODE_STRUCTURE.md
docs/API_CONTRACTS.md
docs/ERROR_CODES.md
docs/DEBUGGING_AND_LOGGING.md
```

## Repository layout

```text
AI_Traffic_Light/
  apps/
    pc-studio/
      backend/              Python / FastAPI backend
      frontend/             React / Vite GUI
    device-camera/
      esp32-cam/            ESP32-CAM firmware placeholder
  packages/
    schema/                 Shared JSON schemas and class definitions
    ui/                     Shared UI component design notes
  config/                   Project-level default config
  docs/                     Instructions and design notes
  samples/                  Sample images/videos/predictions placeholders
  scripts/                  Helper scripts
```

## Next milestone after 0_1_2

The next functional milestone should be:

```text
webcam/video input
→ pretrained YOLO detection
→ zone-based counting
→ rule-based traffic-light simulation
→ GUI visualization
```

Before that, test both receiver and simulation capture and confirm that image/metadata pairs remain after restarting the backend. Do not treat 0_1_2 as passed until the owner confirms every acceptance check.
