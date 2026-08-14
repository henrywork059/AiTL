# PC Studio Function List — 0_1_4 status

This document tracks the main PC Studio functions. Status meanings:

```text
implemented = working candidate behavior that still requires owner acceptance
mock        = simulated/test data behavior only
placeholder = shown in GUI/API but not functionally implemented
later       = outside the current patch scope
```

## Camera functions

| Function | Status | Notes |
|---|---|---|
| Receive uploaded JPEG/PNG frame | implemented | PC-side receiver for future ESP32/Raspberry Pi senders. |
| Preview latest frame | implemented | Automatically refreshes receiver/simulation image. |
| Start/stop simulation | implemented | Moving PNG source for hardware-free testing. |
| Real webcam source | later | Not part of 0_1_4; receiver uploads and simulation are supported. |
| Live inference latency | implemented | Backend reports measured per-frame inference latency. |

## Inference functions

| Function | Status | Notes |
|---|---|---|
| Discover trained models | implemented | Scans `outputs/training/*/weights/best.pt` and orders newest first. |
| Load latest trained model | implemented | Loads newest local `best.pt` with optional Ultralytics backend. |
| Run detection on frame | implemented | Receiver/simulation frame inference with original-coordinate `xyxy` boxes. |
| Filter by confidence | implemented | Backend keeps a 0.10 floor; Live AI applies a higher display threshold without rerunning the same frame. |
| Exact source-frame overlay | implemented | Live AI displays the cached source image used by the returned detections. |
| Instance segmentation | later | After detection + zones. |

## Zone functions

| Function | Status | Notes |
|---|---|---|
| Draw/edit polygon zone | placeholder | Waiting, crossing, vehicle queue, ignore. |
| Save/load zone file | placeholder | Should use shared schema. |
| Count detections inside zones | placeholder | Requires real inference first. |

## Traffic logic functions

| Function | Status | Notes |
|---|---|---|
| Show pedestrian/vehicle counts | mock | Uses mock detection data. |
| Decide signal phase | mock | Rule-based simulation only. |
| Explain decision | mock | Existing traffic simulation explanation. |
| Physical traffic signal control | later | Explicitly not implemented; public-road control is outside project scope. |

## Dataset functions

| Function | Status | Notes |
|---|---|---|
| Capture raw frame | implemented | Saves receiver or simulation image. |
| Save capture metadata | implemented | Paired JSON with source, resolution, quality, note, paths. |
| Mark useful/bad at capture time | implemented | Bad captures are excluded from managed training builds. |
| Browse captured frames | implemented | Dataset Review lists persisted capture metadata. |
| Draw manual bounding boxes | implemented | Uses shared class IDs 0–5. |
| Save/remove manual labels | implemented | Persists separate label JSON files. |
| Save reviewed zero-box negative | implemented | Distinct from an unreviewed frame. |
| Automatic/pseudo labeling | later | Not implemented in 0_1_4. |
| Build YOLO train/val dataset | implemented | Deterministic split under `datasets/yolo/`. |
| Detect stale managed dataset | implemented | Label changes require rebuild before default managed training. |

## Training/export functions

| Function | Status | Notes |
|---|---|---|
| Select dataset YAML | implemented | Must remain inside `datasets/`. |
| Select base model/config | implemented | Prototype limits validated by backend. |
| Start local Ultralytics training | implemented | Optional dependency; one background job at a time. |
| Use in-app managed labels | implemented | Default `yolo/data.yaml` is generated from Dataset Review. |
| Discover trained best.pt runs | implemented | Inference status lists recent trained runs; model-comparison metrics remain later. |
| Export runtime package | later | Not implemented in 0_1_4. |

## Debugging functions

| Function | Status | Notes |
|---|---|---|
| Show recent logs | mock | Existing debug API/UI. |
| Stable backend error codes | implemented | See `docs/ERROR_CODES.md`. |
| Request IDs in JSON APIs | implemented | Standard success/error envelopes. |
| Copy debug report | later | Useful future convenience. |
