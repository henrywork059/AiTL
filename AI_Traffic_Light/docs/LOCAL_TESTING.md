# Local Testing Notes (V020)

V020 / `0_2_0` is a candidate. The confirmed passed baseline is V017 / `0_1_7`. Do not mark V020 passed until the owner explicitly confirms the acceptance checklist.

## Automated backend checks

Activate the PC Studio backend virtual environment first, then from `AI_Traffic_Light` run:

```powershell
python .\scripts\test_camera_frame_service.py
python .\scripts\test_camera_simulation_api.py
python .\scripts\test_dataset_capture_delete.py
python .\scripts\test_training_service.py
python .\scripts\test_zone_traffic_services.py
python .\scripts\test_runtime_settings_logs.py
python .\scripts\test_prototype_tools_api.py
python .\scripts\check_structure.py
```

With the backend running:

```powershell
python .\scripts\test_backend_smoke.py
```

## Frontend validation

From `apps\pc-studio\frontend`:

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

## Key V020 manual checks

1. Dashboard and version surfaces report `0_2_0`.
2. Start simulation or upload a device frame, then open Zone Editor; the current camera frame is the editor background.
3. Draw/edit/save a zone over a visible feature. Navigate away and back and confirm geometry persists.
4. Open Live AI and confirm the same saved zones are overlaid on the live camera image.
5. Toggle **Show zones** off/on and confirm only zone graphics change; detections continue normally.
6. Confirm a compact traffic signal is visible at the top-right of the Live AI image and changes with the simulation-only traffic phase.
7. Capture an image, then delete it from Dataset Capture; counts and last-capture state update.
8. Capture another image, save manual labels, delete it in Dataset Review, and confirm image/metadata/labels disappear.
9. If the deleted item was used in a managed YOLO build, confirm the UI reports that the managed dataset requires rebuilding.
10. Recheck V017 training convergence/early stopping, Settings, Logs, Traffic Logic, model selection/default/delete, confidence controls, simulation density/pause, capture, labeling, and training.
11. Confirm no feature controls physical public-road traffic infrastructure.
