# Human Guide

This guide is for the project owner, students, teachers, and anyone reading or using the **AI Traffic Light** repository.

## 1. What this project is

AI Traffic Light is a prototype project for an **AI vision-based adaptive traffic light system**.

The system idea is:

```text
Camera watches a road/crossing scene
→ AI detects pedestrians and vehicles
→ software counts them in defined zones
→ system simulates better traffic-light timing
→ GUI shows detections, counts, warnings, and signal state
```

This project is for controlled testing, school demonstration, and development. It is **not** a certified public-road traffic-control system.

## 2. Main parts of the project

```text
PC Studio App
```

The main computer app. It will eventually handle:

```text
live camera/video input
object detection
future segmentation/tracking
data capture
zone counting
traffic-light simulation
training/review/export tools
```

```text
Device Camera App
```

The camera-side app. It will usually run on ESP32-CAM or a similar camera node. Its job is only:

```text
capture frames
send frames to the PC
provide simple camera settings/status
```

It should not train the model or run heavy AI.

## 3. Recommended development order

Follow this order:

```text
1. Open the placeholder PC GUI.
2. Use mock/fake detection data.
3. Add webcam or video-file input.
4. Add pretrained object detection.
5. Add traffic zones.
6. Count pedestrians and vehicles inside zones.
7. Add traffic-light simulation logic.
8. Add data capture and review tools.
9. Add ESP-CAM input.
10. Add training/fine-tuning only if the pretrained model is not good enough.
```

Do not start with ESP-CAM, segmentation, or training unless there is a specific reason.

## 4. Folder map

```text
AI_Traffic_Light/
  README.md                         project overview
  VERSION                           current project version
  CHANGELOG.md                      version history
  AGENTS.md                         short rules for AI agents
  docs/
    START_HERE.md                   first human orientation
    HUMAN_GUIDE.md                  this file
    AI_AGENT_GUIDE.md               detailed AI-agent instructions
    DEVELOPMENT_WORKFLOW.md         development sequence
    ROADMAP.md                      milestone plan
    VERSIONING.md                   version and patch rules
  apps/
    pc-studio/
      frontend/                     React/Vite GUI placeholder
      backend/                      Python/FastAPI backend placeholder
    device-camera/
      esp32-cam/                    ESP32-CAM firmware placeholder
  packages/
    schema/                         shared JSON/data schemas
    ui/                             shared UI planning/component notes
  samples/                          small sample files
  datasets/                         dataset placeholders
  models/                           model placeholders
  outputs/                          generated output placeholders
```

## 5. GitHub web upload workflow

If you are uploading patches through the GitHub website:

1. Download the patch zip.
2. Unzip it.
3. Open the repository folder on GitHub:

```text
https://github.com/henrywork059/AiTL/tree/main/AI_Traffic_Light
```

4. Upload the changed files into the matching folders.
5. Replace existing files when GitHub asks.
6. Use a clear commit message.

Example commit message:

```text
Patch v0_0_2: add human and AI-agent docs
```

Important: future patch zips should contain **only changed files**, not the whole repository.

## 6. Versioning rule

The project uses underscore versions:

```text
0_0_0 = initial skeleton
0_0_1 = documentation/version cleanup
0_0_2 = human and AI-agent instruction docs
```

Small patches should increase the last number:

```text
0_0_3
0_0_4
0_0_5
```

Larger milestones can use:

```text
0_1_0
0_2_0
```

## 7. What a good first demo should show

A strong first demo should show:

```text
camera/video frame
boxes around pedestrians and vehicles
zones drawn on the road/crossing
counts for pedestrians and vehicles
traffic-light state
reason for the current decision
```

Example display:

```text
Pedestrians waiting: 4
Pedestrians crossing: 1
Vehicles waiting: 7
Current phase: vehicle green
Suggested action: extend pedestrian green next cycle
```

## 8. Safety notes

This project should only simulate traffic-light behavior or control a small model/LED demo.

Safe uses:

```text
classroom demo
model junction
traffic-light GUI simulation
LED traffic-light model
recorded video analysis
human-supervised decision support
```

Unsafe or out-of-scope uses:

```text
controlling real public traffic lights
deploying on public roads without certification
relying on AI detection as the only safety layer
bypassing traffic-signal hardware safety systems
```

## 9. Data privacy notes

Traffic camera data may include people, vehicles, license plates, and school surroundings.

Before saving or sharing real video/images:

```text
check school rules
avoid identifiable faces if possible
avoid publishing license plates
use sample/demo footage when possible
store only what is needed
```

For GitHub, prefer:

```text
small fake samples
placeholder JSON
synthetic/demo images
```

Do not upload large real datasets unless there is approval.

## 10. Human decision checklist before each patch

Before uploading a new patch, check:

```text
Does it match the project version?
Does it only include changed files?
Does it avoid secrets and private data?
Does it keep the PC/device app split?
Does it update CHANGELOG.md and VERSION if needed?
Does it avoid public-road deployment claims?
```

## 11. Current status

Current patch: **0_0_2**

Current focus:

```text
documentation hygiene
clear rules for AI agents
clear instructions for humans
safe project scope
```

Next likely development step:

```text
0_0_3 or 0_1_0: first runnable webcam/video detection prototype
```
