# PC Studio GUI Layout — V020 candidate

The PC Studio keeps the established sidebar + page-content layout. V020 adds camera-aligned zone editing, capture deletion, and Live AI overlays without restructuring the application.

## Global layout

```text
Operate
- Dashboard          current version and smoke status
- Live AI            camera/simulation frame + trained-model detections + saved zones + compact simulated signal
- Cameras            receiver + controllable synthetic scene

Traffic setup
- Zones              persistent polygon editor directly over the current camera/simulation frame
- Logic              live detection-centre counts + simulation recommendation

Data & model
- Capture            persistent frame capture + delete-latest action
- Review / Label     browse/delete captures + manual boxes + managed YOLO build
- Train              local training + convergence plot + early stopping
- Models             model registry/load/default/delete

System
- Settings           persistent runtime settings
- Logs               recent real backend log buffer
```

## Live AI page

The image area now layers, from back to front:

```text
camera/simulation frame
saved zone polygons
trained-model detection boxes/labels
compact simulation-only traffic signal (top-right)
```

Zone graphics can be hidden with **Show zones** without changing inference or traffic counting.

## Zone Editor

The editor uses the current `/api/camera/frame` as its background. The camera image is mapped into the existing 1280×720 zone-reference coordinate space so saved polygons remain compatible with the backend's live zone-counting logic. Persisted zones are then scaled into the active frame resolution when shown on Live AI.

## Dataset pages

Capture deletion is deliberately destructive and requires user confirmation. One delete removes the raw image, paired capture metadata, and saved manual-label JSON. A previously built managed YOLO dataset may become stale and require rebuilding.

## Train page

The training form and current-run summary remain at the top. The full-width **Training convergence** panel plots per-epoch validation fitness and mAP50-95 and shows best epoch plus the no-improvement/patience counter.

## Safety boundary

No GUI surface sends commands to physical traffic lights. The compact signal and traffic decisions are supervised prototype/simulation output only.
