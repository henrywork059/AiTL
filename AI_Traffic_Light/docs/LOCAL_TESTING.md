# Local Testing Guide — 0_1_1

This guide is for testing the first runnable mock version of the PC Studio app.

## Test goal

Confirm that the project can run locally and that the frontend can read mock data from the backend.

This is not a real AI version yet.

## Requirements

Install these first:

```text
- Python 3.11 or newer recommended
- Node.js 20 or newer recommended
- npm
- Git optional
```

## Backend test

From the project root:

```bat
scripts\start_pc_studio_backend_windows.bat
```

Expected:

```text
Uvicorn running on http://127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
http://127.0.0.1:8000/api/smoke/status
```

Expected:

```text
- /docs opens
- /health returns ok=true
- /api/smoke/status returns checks and endpoint list
```

## Frontend test

Open another terminal and run:

```bat
scripts\start_pc_studio_frontend_windows.bat
```

Open:

```text
http://localhost:5173
```

Expected:

```text
- Dashboard renders
- Sidebar page navigation works
- Live AI page shows mock road scene
- Detection boxes and zones are visible
- Confidence slider filters detections
- Logs page shows mock logs
- Bottom status bar shows API status
- Camera Sources page shows receiver status
- Start simulation displays moving test frames
```

## Camera receiver test

Open **Camera Sources** and select **Start simulation**. The preview should update about twice per second. Stop simulation to return to device receiver mode.

To test a real file upload from another terminal:

```bash
curl -X POST "http://127.0.0.1:8000/api/camera/frame?source_id=test_camera" -H "Content-Type: image/jpeg" --data-binary "@test-frame.jpg"
```

The preview should display the uploaded image within about one second. For a camera device on the same network, replace `127.0.0.1` with the PC's LAN IP address and allow TCP port 8000 through the private-network firewall. Keep this development server on a trusted private network; the receiver does not yet implement camera authentication.

## Smoke test script

With the backend running:

```bat
scripts\test_backend_smoke_windows.bat
```

Expected:

```text
[PASS] /health
[PASS] /api/smoke/status
[PASS] /api/mock/frame
[PASS] /api/mock/zones
[PASS] /api/traffic/state
[PASS] /api/logs/recent
```

## If the frontend says fallback mode

Fallback mode means the frontend started but could not reach the backend.

Check:

```text
- Is the backend terminal still running?
- Is the backend at http://127.0.0.1:8000?
- Did pip install complete successfully?
- Is another app already using port 8000?
```

The frontend can still render local mock data in fallback mode, but that does not confirm backend connection.

## What is not expected to work

```text
- real camera stream
- ESP32/Raspberry Pi camera firmware
- real object detection
- training
- model export
- physical traffic-light output
```
