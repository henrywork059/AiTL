# Architecture

## High-level architecture

```text
ESP-CAM / webcam / video file
        ↓
PC Studio backend
        ↓
Detection / tracking / counting
        ↓
Traffic decision engine
        ↓
PC Studio frontend GUI
        ↓
Viewer / dataset capture / traffic-light simulator
```

## Two-app design

### 1. PC Studio App

The PC Studio App is the main application.

Responsibilities:

- Receive frames from webcam, video file, IP camera, or ESP-CAM.
- Run object detection or segmentation.
- Count pedestrians and vehicles inside zones.
- Simulate traffic-light logic.
- Show live GUI.
- Save frames and labels.
- Train or fine-tune models later.
- Export model/runtime package later.

### 2. Device Camera App

The device camera app is lightweight firmware.

Responsibilities:

- Connect to Wi-Fi.
- Capture camera frames.
- Send MJPEG/JPEG frames to PC.
- Expose simple status/config endpoints.

It should not train models and should not run heavy AI.

## Shared schemas

Use shared schemas for detections, zones, traffic state, and camera metadata. This prevents the PC app, GUI, and future device code from using incompatible formats.

## Development mode

Version 1 starts with mock data:

```text
Fake camera frame
+ fake detections
+ fake counts
+ fake traffic state
```

This allows GUI development with hot reload before AI and camera hardware are connected.
