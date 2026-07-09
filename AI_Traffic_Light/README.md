# AI Traffic Light — 0_0_x Prototype Project

This repository contains the early skeleton for an **AI vision-based adaptive traffic light project**.

The project is currently in the **0_0_x planning/template stage**. The current patch is **0_0_4**, which adds the first structured **PC Studio App template** for confirming the function list and GUI layout before real AI/camera/training implementation.

## Project concept

```text
Camera/video input
→ object detection for pedestrians and vehicles
→ zone-based counting
→ traffic-light decision simulation
→ GUI visualization and dataset capture
```

This is a **prototype and simulation project**. It must not be connected to real public traffic-light infrastructure.

## Main apps

### 1. PC Studio App

Runs on the computer. Planned responsibilities:

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

Runs on an ESP32-CAM or similar camera node. Planned responsibilities:

- capture frames
- send frames to the PC
- expose simple camera status/settings

The device app should not train AI and should not run heavy segmentation/detection models in the first design.

## Current version

```text
0_0_0 = initial skeleton
0_0_1 = documentation/version cleanup
0_0_2 = human and AI-agent docs
0_0_3 = modular code, API, logging, and error-code standards
0_0_4 = PC Studio app template and function map
```

## Important docs

Start here:

```text
docs/START_HERE.md
docs/HUMAN_GUIDE.md
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
      backend/              Python / FastAPI backend placeholder
      frontend/             React / Vite GUI placeholder
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

## First milestone

The first real milestone is still:

```text
Video/webcam input
→ pretrained object detection
→ zone-based counting
→ rule-based traffic-light simulation
→ GUI visualization
```

But before implementing that, **0_0_4 asks humans and AI agents to confirm the PC Studio page list, function list, and GUI layout**.
