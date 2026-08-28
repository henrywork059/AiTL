# Patch 0_3_2 — PC-pull ESP32-CAM integration

## Release state

- Candidate: V032 / `0_3_2`
- Previous candidate: V031 / `0_3_1`
- Owner-confirmed passed baseline: V024 / `0_2_4`
- V031 is not promoted by this patch.

## Goal

Make the already-working Arduino IDE `CameraWebServer` example usable directly from PC Studio by entering the ESP32-CAM IP address.

## Implemented

### Backend remote camera service

`app/services/remote_camera.py`:

- validates one literal RFC1918 private IPv4 address and refuses redirect-following from the fixed `/capture` target;
- probes `GET http://<ESP-IP>/capture` before accepting the connection;
- ingests JPEG bytes through the existing `camera_frame_service.store_upload`;
- runs one daemon pull worker with bounded 100–5000 ms interval;
- records connection/fetch/error/frame telemetry;
- pauses ingestion while Camera Sources simulation is active;
- resumes automatically when simulation stops;
- stops the worker during FastAPI shutdown.

### Camera API

New routes:

- `GET /api/camera/remote/status`
- `POST /api/camera/remote/connect`
- `POST /api/camera/remote/disconnect`

Connect body:

```json
{
  "host": "192.168.1.87",
  "source_id": "esp32_cam_01",
  "fetch_interval_ms": 500
}
```

Existing routes are retained, including raw image upload.

### PC Studio

Camera Sources now provides:

- ESP IPv4 input;
- source ID input;
- Connect / Reconnect / Disconnect;
- remote health state;
- current ESP address and pull counters;
- direct CameraWebServer MJPEG preview when available;
- backend-frame fallback;
- simulation coexistence notice.

### Firmware compatibility

No custom V032 firmware is required for the first physical test. The stock Arduino ESP32 CameraWebServer example is the hardware baseline.

## Deliberate non-changes

- no traffic-light LED output;
- no ESP-side inference;
- no live public-road control;
- no persistence of remote camera configuration;
- no multi-camera independent frame store;
- no removal of legacy device POST upload.

## Errors

No new stable error code is introduced. Existing camera/request codes are reused:

- `ATL-CAMERA-001` unreachable camera;
- `ATL-CAMERA-003` invalid/non-private camera address;
- `ATL-CAMERA-005..007` frame size/type/content validation;
- `ATL-API-002` invalid interval/request fields.

## Acceptance

1. Stock CameraWebServer works in browser.
2. Enter the ESP IP in Camera Sources and press Connect.
3. PC Studio reports connected.
4. Camera Sources shows live image.
5. `/api/camera/status` reports `active_source_id = esp32_cam_01`.
6. Live AI uses the physical camera frame when a model is loaded.
7. Dataset Capture saves a physical-camera frame.
8. Start simulation: remote status says paused for simulation and synthetic frames take over.
9. Stop simulation: physical ESP frames resume without reconnecting.
10. Disconnect: worker stops and the last frame simply becomes stale.
11. A public IP such as `8.8.8.8` is rejected.
12. Full inherited regression/typecheck/build/live smoke passes before owner acceptance.

Owner acceptance is required before `passed_baseline` changes.
