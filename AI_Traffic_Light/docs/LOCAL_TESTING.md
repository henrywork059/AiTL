# Local Testing Notes — V033

## Version

Expected:

```text
version: 0_3_3
previous_version: 0_3_2
passed_baseline: 0_2_4
```

## Software checks

From `AI_Traffic_Light`:

```powershell
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\test_remote_camera_session.py"
& $py ".\scripts\check_structure.py"
```

Then run all inherited non-live regression scripts, frontend `npm ci`, `npm run typecheck`, `npm run build`, live backend smoke, and `git diff --check`.

## Physical acceptance

1. Flash V033 Arduino firmware.
2. Confirm Serial Monitor shows `session=idle`.
3. In a browser open `http://<ESP-IP>/status`.
4. Confirm `/capture` returns conflict while idle.
5. In PC Studio enter the ESP IP and click **Connect**.
6. Confirm PC reports **ESP ready** but ESP `capture_count` remains unchanged.
7. Choose resolution/quality/settings.
8. Click **Start Stream**.
9. Confirm settings appear in ESP `/status`.
10. Confirm `session_active=true`.
11. Confirm PC frame counter and ESP capture counter increase.
12. Click **Stop Stream**.
13. Confirm ESP returns to `session_active=false` and capture counter stops increasing.
14. Start/stop simulation while ESP stream is active; PC requests must pause/resume without reconnecting.
15. Confirm Dataset Capture and Live AI consume the physical frame.
16. Confirm legacy raw frame upload still works.

Only explicit owner acceptance may change `passed_baseline`.
