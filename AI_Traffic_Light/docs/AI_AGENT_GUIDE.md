# AI Agent Guide

This guide is for AI coding agents, ChatGPT-style assistants, documentation agents, and automated project helpers working on **AI Traffic Light**.

The root `AGENTS.md` contains the short mandatory rules. This file explains how to apply them.

## 1. Project purpose

AI Traffic Light is a student-scale computer vision project. The intended system is:

```text
Camera/video input
→ object detection or future segmentation
→ pedestrian/vehicle counting inside traffic zones
→ rule-based traffic-light simulation
→ GUI visualization and dataset capture
```

The project should demonstrate adaptive signal logic, not control real public traffic infrastructure.

Use these descriptions:

```text
prototype
simulation
model junction
traffic-light demo
AI vision decision-support system
```

Avoid these descriptions unless the user explicitly changes the project scope and provides safety certification requirements:

```text
production traffic controller
real road deployment
certified safety system
public-road autonomous signal control
```

## 2. System architecture

Keep the two-part app structure:

```text
PC Studio App
- receives camera/video frames
- runs AI detection/segmentation
- counts traffic objects inside zones
- simulates signal decisions
- captures datasets
- reviews data and predictions
- later trains and exports models

Device Camera App
- runs on ESP32-CAM or similar camera node
- captures frames
- sends frames to the PC
- provides basic camera status/configuration
- does not train AI
- does not run heavy inference
```

Shared contracts live in:

```text
packages/schema/
packages/ui/
```

Do not create separate incompatible detection formats for the PC app and device app.

## 3. Versioning and patch packaging

The project uses underscore versions:

```text
0_0_0
0_0_1
0_0_2
```

Patch zip rule:

```text
Only include changed files.
Keep the same relative paths.
Do not include the whole repo unless requested.
```

Correct patch structure example:

```text
AI_Traffic_Light/
  README.md
  VERSION
  CHANGELOG.md
  docs/
    PATCH_0_0_3.md
    SOME_CHANGED_DOC.md
```

Wrong patch structure example:

```text
AI_Traffic_Light_0_0_3_full_project/
  entire repository...
```

When producing a patch, include:

```text
VERSION update
CHANGELOG update
PATCH_<version>.md note
changed code/docs only
```

## 4. Documentation rules

Documentation should serve two audiences:

1. Humans: students, teachers, project reviewers, future maintainers.
2. AI agents: tools that need clear repository rules and safe editing boundaries.

For humans, explain:

```text
what the feature is
how to run or use it
what it does not do yet
what the next step is
```

For AI agents, specify:

```text
which files are relevant
what must not be changed
what assumptions are safe
what output/versioning format to use
```

## 5. Safety boundaries

Traffic control is safety-critical. This project must stay in the prototype/simulation scope unless the user explicitly creates a separate certified deployment plan.

Do not write code or docs that imply:

```text
direct connection to real traffic-light cabinets
bypassing traffic-signal safety interlocks
unsafe autonomous public-road control
using unverified detections as sole control authority
```

Acceptable outputs include:

```text
simulated light state
LED model traffic light
GUI recommendation
human-supervised extension suggestion
controlled classroom test track
```

## 6. CV/AI design assumptions

Use a staged development path:

```text
1. Mock/fake data GUI
2. Webcam or video-file input
3. Pretrained object detection
4. Zone-based counting
5. Rule-based signal simulation
6. Dataset capture/review
7. ESP-CAM input
8. Fine-tuning/training if needed
9. Segmentation or tracking if needed
```

Do not start with segmentation, multi-camera fusion, or custom model training unless the user specifically asks.

## 7. Data schema expectations

Prefer detection data like:

```json
{
  "frame_id": "cam01_000001",
  "source_id": "cam01",
  "image_width": 1280,
  "image_height": 720,
  "timestamp_ms": 123456,
  "detections": [
    {
      "id": "det_001",
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.91,
      "box_xyxy": [120, 80, 260, 420]
    }
  ]
}
```

Important rule:

```text
Store boxes in original image coordinates.
Convert to displayed coordinates only inside the viewer/overlay layer.
```

Avoid saving GUI canvas coordinates as the main data record.

## 8. GUI development expectations

The project should support fast visual development:

```text
Vite frontend hot reload
FastAPI backend reload
mock frames
fake detection JSON
fake traffic-light states
```

A GUI page should be able to load without:

```text
real camera
real ESP-CAM
trained model
GPU
internet connection
```

When adding GUI features, provide mock/sample states first.

## 9. File and folder discipline

Use these locations:

```text
apps/pc-studio/frontend/       React/Vite app
apps/pc-studio/backend/        FastAPI/Python backend
apps/device-camera/esp32-cam/  ESP32-CAM firmware
packages/schema/               shared JSON/data schemas
packages/ui/                   shared UI/component notes or future components
docs/                          project documentation
samples/                       small sample files only
models/                        placeholders only unless user approves model files
datasets/                      placeholders only unless user approves data files
outputs/                       generated files, usually not committed
```

Do not put random scripts at repo root unless they are project-wide helpers.

## 10. Commit and patch message style

Use short, versioned messages:

```text
Patch v0_0_2: add human and AI-agent docs
Patch v0_0_3: add webcam detection prototype
Patch v0_0_4: add zone-counting service
```

For GitHub web upload, the user may manually upload changed files. Patch zips should make this easy.

## 11. When uncertain

If a requirement is ambiguous, choose the smallest safe prototype-friendly interpretation. Do not overbuild.

Prefer:

```text
mock first
document assumptions
keep files small
avoid hardware dependency
avoid safety-critical claims
```

Then leave a clear note in `docs/PATCH_<version>.md`.
