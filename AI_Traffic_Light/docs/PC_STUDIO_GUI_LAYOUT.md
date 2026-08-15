# PC Studio GUI Layout — V017 candidate

The PC Studio keeps the established sidebar + page-content layout. V017 converts the remaining main mock/template pages into working prototype surfaces without restructuring the application.

## Global layout

```text
Operate
- Dashboard          current version and smoke status
- Live AI            camera/simulation frame + trained-model detections
- Cameras            receiver + controllable synthetic scene

Traffic setup
- Zones              persistent polygon editor on a 1280 x 720 reference
- Logic              live detection-centre counts + simulation recommendation

Data & model
- Capture            persistent frame capture
- Review / Label     manual bounding boxes + managed YOLO build
- Train              local training + convergence plot + early stopping
- Models             model registry/load/default/delete

System
- Settings           persistent runtime settings
- Logs               recent real backend log buffer
```

## Train page

The training form and current-run summary remain at the top. A full-width **Training convergence** panel below them plots per-epoch validation fitness and mAP50-95 and shows best epoch plus the no-improvement/patience counter.

## Zone / traffic pages

The Zone Editor saves polygons to local runtime configuration. Traffic Logic scales current trained-model detection centres into the same reference coordinate system and generates simulation-only recommendations from pedestrian waiting/crossing and vehicle queue counts.

## Safety boundary

No GUI surface sends commands to physical traffic lights. Traffic decisions remain supervised prototype/simulation output only.
