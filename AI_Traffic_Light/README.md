# AI Traffic Light — 0_1_1 Camera Receiver Project

This repository contains an early **AI vision-based adaptive traffic light project**.

The current version is **0_1_1**, a test-ready PC camera-frame receiver. It accepts JPEG/PNG images from future ESP32 or Raspberry Pi camera nodes, automatically displays the newest frame, and provides a hardware-free simulation mode.

## Project concept

```text
Camera/video input
→ object detection for pedestrians and vehicles
→ zone-based counting
→ traffic-light decision simulation
→ GUI visualization and dataset capture
```

This is a **prototype and simulation project**. It must not be connected to real public traffic-light infrastructure.

## What 0_1_1 can test

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
```

## What 0_1_1 does not implement yet

```text
- ESP32/Raspberry Pi camera firmware
- real webcam capture
- YOLO/object-detection inference
- segmentation
- dataset writing
- training
- model export
- physical traffic-light control
```

## Main apps

### 1. PC Studio App

Runs on the computer. Current 0_1_1 status: **camera receiver and simulation test-ready**.

Planned responsibilities:

- camera/video source management
- live AI detection view
- traffic-zone setup
- pedestrian/vehicle counting
- rule-based traffic-light simulation
- dataset capture
- dataset review
- model training/export placeholders
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

## Current version history

```text
0_0_0 = initial skeleton
0_0_1 = documentation/version cleanup
0_0_2 = human and AI-agent docs
0_0_3 = modular code, API, logging, and error-code standards
0_0_4 = PC Studio app template and function map
0_1_0 = first test-ready mock PC Studio version
0_1_1 = camera frame receiver, live preview, and simulation mode
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

## Next milestone after 0_1_1

The next functional milestone should be:

```text
webcam/video input
→ pretrained YOLO detection
→ zone-based counting
→ rule-based traffic-light simulation
→ GUI visualization
```

Before that, connect an ESP32 or Raspberry Pi sender to the documented frame-upload endpoint.
