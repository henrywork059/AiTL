# PC Studio Function List — Draft 0_0_4

This document defines the first planned function list for the PC Studio App.

Status meanings:

```text
placeholder = shown in GUI/API but not implemented
planned     = should be implemented after layout confirmation
later       = useful later, not needed for the first working prototype
```

## Camera functions

| Function | Status | Notes |
|---|---|---|
| Add camera source | placeholder | Webcam, ESP-CAM MJPEG, IP camera, video file. |
| Preview stream | placeholder | Show source before AI runs. |
| Start/stop stream | planned | Needed before real detection. |
| Measure FPS/latency | planned | Needed for debugging. |
| Save source settings | later | Useful after app flow is stable. |

## Inference functions

| Function | Status | Notes |
|---|---|---|
| Load model | placeholder | First real model should be pretrained YOLO-style detection. |
| Run detection on frame | placeholder | Return DetectionFrame JSON. |
| Filter by confidence/class | placeholder | Should be frontend and backend compatible. |
| Coordinate conversion | planned | Critical for correct boxes after resizing. |
| Instance segmentation | later | Add after detection + zones work. |

## Zone functions

| Function | Status | Notes |
|---|---|---|
| Draw polygon zone | placeholder | Waiting, crossing, vehicle queue, ignore. |
| Edit polygon points | planned | Needed for real scenes. |
| Save/load zone file | planned | Should use shared schema. |
| Count detections inside zones | placeholder | Core traffic logic input. |

## Traffic logic functions

| Function | Status | Notes |
|---|---|---|
| Compute pedestrian count | placeholder | Waiting and crossing separately. |
| Compute vehicle queue count | placeholder | Cars, buses, trucks, motorcycles, bicycles. |
| Decide signal phase | placeholder | Rule-based first. |
| Explain decision | planned | Required for demo and debugging. |
| Safety override | later | Simulation only; no real public traffic control. |

## Dataset functions

| Function | Status | Notes |
|---|---|---|
| Capture raw frame | placeholder | Saves image. |
| Save detection JSON | placeholder | Saves model output with frame. |
| Mark useful/bad | planned | Helps dataset cleanup. |
| Review captured frames | placeholder | Page exists; functionality later. |
| Export dataset | later | Needed before training. |

## Training/export functions

| Function | Status | Notes |
|---|---|---|
| Select dataset | placeholder | Layout only. |
| Select base model | placeholder | Layout only. |
| Start training | later | Not part of first demo. |
| Compare model versions | later | After at least two models exist. |
| Export runtime package | later | For later device/PC deployment package. |

## Debugging functions

| Function | Status | Notes |
|---|---|---|
| Show recent logs | placeholder | Frontend page and backend endpoint exist. |
| Show error codes | planned | Use docs/ERROR_CODES.md as source. |
| Copy debug report | later | Helpful when asking AI agents for help. |
