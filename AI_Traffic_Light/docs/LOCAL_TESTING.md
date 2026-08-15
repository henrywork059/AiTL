# Local Testing Notes (V017)

V017 is a candidate. Do not mark it passed until the owner explicitly confirms the acceptance checklist.

## Automated backend checks

From `AI_Traffic_Light`:

```powershell
python .\scripts\test_camera_frame_service.py
python .\scripts\test_camera_simulation_api.py
python .\scripts\test_training_service.py
python .\scripts\test_zone_traffic_services.py
python .\scripts\test_runtime_settings_logs.py
python .\scripts\test_prototype_tools_api.py
python .\scripts\test_backend_smoke.py
python .\scripts\check_structure.py
```

`test_backend_smoke.py` requires the backend to be running. The other focused service/API scripts should run without a real camera or trained model; the training test uses a fake trainer to test orchestration without doing GPU training.

## Frontend validation

From `apps\pc-studio\frontend`:

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

## Key V017 manual checks

1. Dashboard **Project stage** shows `0_1_7`; no `0_1_5` or `0_1_6` candidate label remains in the visible PC Studio navigation/status surfaces.
2. Build a current managed YOLO dataset and start a training run with more maximum epochs than patience.
3. After the first train+validation epoch, confirm the **Training convergence** plot begins adding points.
4. Confirm fitness/mAP history updates while the run advances and the best epoch / no-improvement counter changes.
5. Use a small patience value for testing. If validation fitness plateaus long enough, confirm Ultralytics stops before the maximum epoch count and the UI reports `early_stopped`.
6. Confirm `best.pt` is still discoverable after an early-stopped run.
7. Open **Zone Editor**. Select a zone, edit polygon points, Apply draft, Save zones, leave the page, return, and confirm the saved geometry persists.
8. Reset zones and confirm the vertical-crossing reference configuration returns.
9. Start simulation, load a trained model, then open **Traffic Logic**. Confirm current frame number/zone counts update and the decision reason is derived from detected people/vehicles.
10. Confirm Traffic Logic says prototype/simulation only and nothing controls physical signals.
11. Open **Settings**, change confidence / camera-status poll interval / default training patience / log level, save, reload the page, and confirm persistence.
12. Open **Logs & Errors** and confirm real backend events, timestamps, scopes, and request IDs appear instead of fixed mock log rows.
13. Recheck V016 Live AI model text containment, simulation density, pause/resume, capture, labeling, model management, confidence controls, and class visibility.
