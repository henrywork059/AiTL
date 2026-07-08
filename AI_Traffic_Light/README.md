# AI Traffic Light — Initial Project Skeleton

Current patch: **0_0_1**  
Baseline skeleton: **0_0_0**

This repository contains the starter structure for an **AI vision-based adaptive traffic light project**.

The project is designed around two main parts:

1. **PC Studio App**
   - Runs on the computer.
   - Receives camera/video frames.
   - Runs object detection and possible future segmentation.
   - Counts pedestrians and vehicles inside traffic zones.
   - Simulates traffic-light decisions.
   - Captures datasets and later trains/exports models.

2. **Device Camera App**
   - Runs on an ESP32-CAM or similar camera node.
   - Captures frames and sends them to the PC.
   - Does **not** train AI and does **not** run heavy AI inference.

The current project state is a **starter skeleton**, not a finished product. It contains placeholder GUIs, mock APIs, schemas, documentation, and folder structure so development can begin cleanly.

## Recommended first milestone

Build this before adding ESP-CAM or custom training:

```text
Video/webcam input
→ pretrained object detection
→ zone-based counting
→ rule-based traffic-light simulation
→ GUI visualization
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

## Development direction

- Use the PC app first with fake/mock data.
- Add webcam/video input next.
- Add YOLO detection after the GUI flow works.
- Add ESP-CAM stream only after the PC prototype is stable.
- Add training after the detection + zone logic is proven.

## Version status

- **0_0_0**: initial starter skeleton.
- **0_0_1**: documentation and version-wording cleanup.

No functional app behavior is expected from this patch beyond corrected documentation/version labels.
