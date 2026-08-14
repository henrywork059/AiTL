# AI Traffic Light — 0_1_3 Manual Labeling Project

This repository contains an early **AI vision-based adaptive traffic-light prototype**.

The current candidate is **0_1_3**. It receives or simulates camera frames, persistently captures selected images, lets a human draw and save bounding-box labels in PC Studio, and can convert reviewed captures into a managed YOLO train/validation dataset for the existing optional Ultralytics training runner.

## Project concept

```text
Camera/video input
→ human-supervised dataset capture and labeling
→ object detection for pedestrians and vehicles
→ zone-based counting
→ traffic-light decision simulation
→ GUI visualization
```

This is a **prototype and simulation project**. It must not be connected to real public traffic-light infrastructure.

## What 0_1_3 can test

```text
- PC Studio frontend and FastAPI backend startup
- frontend ↔ backend mock API connection
- raw JPEG/PNG frame upload to the PC
- moving PNG camera simulation without hardware
- persistent receiver/simulation image capture with JSON metadata
- capture sessions, notes, and quality tags
- browsing saved captures in Dataset Review
- manual bounding-box labeling for the shared six classes
- reviewed zero-box negative examples
- persistent label JSON files
- exclusion of bad-quality captures from managed training data
- deterministic YOLO train/validation dataset generation
- generated datasets/yolo/data.yaml and manifest
- stale managed-dataset detection after label edits
- optional background Ultralytics YOLO training from the managed or another labeled dataset
```

The shared labeling classes are:

```text
0 person
1 car
2 bus
3 truck
4 motorcycle
5 bicycle
```

## What 0_1_3 does not implement yet

```text
- ESP32/Raspberry Pi camera firmware
- real webcam capture
- automatic object labeling
- YOLO/object-detection inference in the live view
- segmentation
- model export
- physical traffic-light control
```

## Main apps

### 1. PC Studio App

Runs on the computer. Current 0_1_3 status: **manual-labeling candidate awaiting owner acceptance**.

Current testable data workflow:

```text
Camera Sources
→ Dataset Capture
→ Dataset Review / manual labels
→ Build training dataset
→ Train / Export (optional Ultralytics dependency)
```

### 2. Device Camera App

Runs on an ESP32-CAM or similar camera node. Current status: **placeholder only**.

The device app should capture/send frames only. Training and dataset labeling stay on the PC.

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

Generated captures remain under:

```text
datasets/captures/<session_id>/images/
datasets/captures/<session_id>/metadata/
datasets/captures/<session_id>/labels/
```

After at least two non-bad captures have been reviewed and their labels saved, **Dataset Review → Build training dataset** creates:

```text
datasets/yolo/images/train/
datasets/yolo/images/val/
datasets/yolo/labels/train/
datasets/yolo/labels/val/
datasets/yolo/data.yaml
datasets/yolo/manifest.json
```

`datasets/` and `outputs/` are generated runtime content and must not be included in patch ZIPs.

For optional real YOLO training, install the extra dependency from the backend folder:

```powershell
pip install -r requirements-training.txt
```

Then use the default `yolo/data.yaml` on **Train / Export**, or another labeled YOLO YAML path inside `datasets/`.

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
0_1_3 = manual bounding-box labeling and managed YOLO dataset generation
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

## Next functional milestone

After 0_1_3 is accepted, the next useful milestone can connect a pretrained detector to captured/live frames, then feed detections into zone-based counting and the existing traffic-light simulation. That later inference work must remain separate from real public-road control.

Do not treat 0_1_3 as passed until the project owner confirms every required acceptance check.
