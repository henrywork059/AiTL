# Local Testing — V034

Expected version:

```text
version: 0_3_4
previous_version: 0_3_3
passed_baseline: 0_2_4
```

Run the normal update/test workflow:

```powershell
.\scripts\update_test_run.ps1
```

Focused checks must include `test_remote_camera_pull.py` and `test_remote_camera_session.py`.

## Physical performance acceptance

1. Flash V034 ESP firmware.
2. Connect in PC Studio; confirm zero image transfer before Start Stream.
3. Start with VGA / JPEG quality 12–16 / 15 FPS.
4. Confirm remote status shows `transport=mjpeg`.
5. Confirm `measured_fps` approaches the selected target without a rising reconnect count.
6. Move an object quickly in front of the camera and verify Camera Sources motion is substantially smoother than V033.
7. Try 20 FPS. Keep it only if measured FPS and latency remain stable.
8. Start simulation and confirm ESP stream traffic pauses; stop simulation and confirm it resumes.
9. Test Live AI and Dataset Capture on physical frames.
10. Run full inherited backend/frontend/smoke/git checks before owner acceptance.
