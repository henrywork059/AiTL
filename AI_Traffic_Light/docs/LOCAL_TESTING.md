# Local Testing Notes (V016)

## Key manual tests

1. Confirm `GET /health` and the Dashboard show `0_1_6`.
2. Open **Live AI** with a trained model whose run ID/path is long. Confirm Active run, Default run, Path, and Run folder wrap inside the Trained model panel instead of extending beyond its border.
3. Open **Camera Sources** and start simulation mode.
4. Confirm the zebra crossing is a vertical travel corridor: white zebra bars run horizontally across it while pedestrians move from the top of the image toward the bottom.
5. Confirm cars/buses move left-to-right or right-to-left on horizontal road lanes.
6. Leave the scene running for several seconds and confirm pedestrian positions/counts and vehicle layout vary rather than showing one fixed person/car arrangement.
7. Change **Scene density** through Light, Normal, and Busy. Confirm the visible synthetic population changes and status reports the selected density.
8. Click **Pause scene**. Confirm the frame number/image stops advancing and the status reports paused; click **Resume scene** and confirm movement returns.
9. While paused, use the existing Dataset Capture page to save the frame and confirm persistent capture still works.
10. Return to **Live AI** and confirm V015 model selection, default model, confidence, box/label toggles, and class filters still work.
11. Confirm no live detection is connected to physical traffic-light control.

## Automated local commands

From `AI_Traffic_Light`:

```powershell
python .\scripts\test_camera_frame_service.py
python .\scripts\test_camera_simulation_api.py
python .\scripts\test_backend_smoke.py
python .\scripts\check_structure.py
```

From `apps\pc-studio\frontend`:

```powershell
npm run typecheck
npm run build
```
