# GUI Plan

## PC Studio App pages

### 1. Live AI View

Purpose:

- Show camera/video frame.
- Draw detection boxes and zones.
- Display object counts.
- Show current traffic-light phase.
- Show suggested next action.

### 2. Camera Sources

Purpose:

- Add webcam / video file / ESP-CAM stream.
- Preview camera status.
- Show FPS and latency.

### 3. Zone Setup

Purpose:

- Define pedestrian waiting zone.
- Define crossing zone.
- Define vehicle queue zone.
- Define ignore zone.

The initial skeleton uses hard-coded zones. A later version should add a visual zone editor.

### 4. Dataset Capture

Purpose:

- Save frames.
- Save detection JSON.
- Mark useful or bad samples.
- Prepare data for annotation/training.

### 5. Review / Label

Purpose:

- Browse saved frames.
- Compare labels and predictions.
- Inspect false positives and false negatives.

### 6. Train / Export

Purpose:

- Configure model training.
- View training logs.
- Export model package for runtime.

This is a placeholder in the initial skeleton.

## Main live view layout

```text
┌──────────────────────────────────────────┬────────────────────────────┐
│ Live camera / video frame                │ Traffic light simulator    │
│ Detection boxes + zones                  │ Counts                     │
│                                          │ Current phase              │
│                                          │ Next decision              │
├──────────────────────────────────────────┴────────────────────────────┤
│ Controls: source, confidence, class filter, start/stop, capture        │
└───────────────────────────────────────────────────────────────────────┘
```

## Required placeholder states

- No camera connected.
- Mock frame loaded.
- Detection running.
- Detection stopped.
- High pedestrian demand.
- High vehicle demand.
- Pedestrian still crossing.
- Error state.
