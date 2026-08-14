# Patch 0_1_3 — Manual labeling and managed YOLO dataset

## Purpose

Close the gap between 0_1_2 persistent capture and its optional YOLO training runner without replacing either architecture. PC Studio can now manually label saved capture images and convert those reviews into the default `datasets/yolo/data.yaml` training dataset.

The previous passed baseline remains 0_1_1 until the project owner accepts this candidate. 0_1_3 is built on the current 0_1_2 `main` implementation because capture and the training runner are prerequisites for this patch.

## Implemented workflow

1. Capture receiver or simulation frames using the existing **Dataset Capture** page.
2. Open **Dataset Review**.
3. Select a persisted frame.
4. Choose one of the shared classes: person, car, bus, truck, motorcycle, bicycle.
5. Drag bounding boxes over visible objects.
6. Remove incorrect boxes if needed.
7. Select **Save labels**.
8. Repeat for at least two non-bad frames. Saving zero boxes is allowed for a human-reviewed negative example.
9. Select **Build training dataset**.
10. The backend creates a deterministic YOLO train/validation split under `datasets/yolo/`.
11. Open **Train / Export**. The existing default `yolo/data.yaml` now points to data created by the in-app labeling workflow.

## Storage

Original capture files remain unchanged:

```text
datasets/captures/<session>/images/
datasets/captures/<session>/metadata/
```

Manual reviews are added separately:

```text
datasets/captures/<session>/labels/<capture_id>.json
```

Managed training files are generated at runtime:

```text
datasets/yolo/images/train/
datasets/yolo/images/val/
datasets/yolo/labels/train/
datasets/yolo/labels/val/
datasets/yolo/data.yaml
datasets/yolo/manifest.json
```

These folders are generated/private data and are not included in the patch ZIP.

## Dataset rules

- Shared class IDs come from `packages/schema/classes.default.json`.
- The browser/server derives class names from that schema; the UI cannot create arbitrary class IDs/names.
- Boxes use pixel `x1,y1,x2,y2` coordinates while editing and are validated against the stored capture resolution.
- YOLO export converts boxes to normalized center/width/height format.
- A saved zero-box review is a valid negative example.
- An unreviewed frame is not silently treated as a negative example.
- Captures tagged `bad` are excluded from managed training builds.
- At least two eligible reviewed frames are required so train and validation remain distinct.
- Split membership is deterministic from capture IDs.
- The build manifest stores a signature of the source review state. Label changes after a build mark `yolo/data.yaml` stale until rebuilt.

## Training integration

The existing 0_1_2 Ultralytics runner remains optional. Install it with:

```powershell
Set-Location ".\AI_Traffic_Light\apps\pc-studio\backend"
pip install -r requirements-training.txt
```

The default Train / Export dataset path remains:

```text
yolo/data.yaml
```

When that default is selected, the frontend blocks training until the managed dataset is current. Existing custom labeled YOLO YAML paths inside `datasets/` remain supported.

## Limitations

This patch does not implement:

```text
- automatic/pseudo labeling
- model-assisted box proposals
- box resize handles after drawing (remove and redraw instead)
- class-schema editing in the GUI
- live YOLO inference
- model export
- training cancellation/resume
- real public-road signal control
```

## Safety and data boundaries

Captured images and labels may contain personal data. Collect, label, retain, and train on them only with appropriate permission and data-handling controls.

This remains a supervised traffic-light simulation/classroom prototype. It does not control real public-road traffic infrastructure.

0_1_3 is a candidate until the owner completes `docs/TEST_READY_CHECKLIST.md` and explicitly confirms success.
