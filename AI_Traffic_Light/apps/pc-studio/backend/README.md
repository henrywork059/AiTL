# PC Studio Backend

FastAPI backend for the local AiTL computer-vision and traffic-light simulation prototype. Root `AI_Traffic_Light/VERSION` is the release-state authority.

## Main responsibilities

- receive/store the latest device frame and run the synthetic signal-aware camera;
- pull stock Arduino ESP32 CameraWebServer JPEG snapshots from a configured private-LAN IP;
- dataset capture/delete/label/build workflow;
- local Ultralytics training/model registry/live inference;
- camera-aligned zones, sampled occupancy, tracking and flow events;
- ranked simulated signal scenarios and protected phase timing;
- isolated single-junction and seven-mode two-intersection experiments;
- generic intersection/source/topology foundation;
- structured live decision context and normalized experiment evidence;
- runtime settings/logging.

## Camera transport ownership

`services/camera_frames.py` remains the common latest-frame/simulation store.

V032 adds `services/remote_camera.py` as a transport adapter:

```text
stock ESP32 CameraWebServer
        ↓ GET /capture
RemoteCameraService
        ↓ validated JPEG
CameraFrameService
        ↓
inference / dataset / zones / analytics
```

The legacy device push path remains available:

```text
POST /api/camera/frame?source_id=<id>
```

The remote camera service accepts only literal RFC1918 IPv4 addresses, owns its background fetch worker, pauses while the built-in camera simulation is active, and is stopped during FastAPI shutdown.

## Architecture ownership

```text
app/main.py       FastAPI creation/lifecycle/router wiring
app/routes/       HTTP translation
app/services/     domain behavior/state/persistence/inference/training/transports
app/models.py     shared Pydantic contracts
app/core/         envelopes/errors/logging/middleware/version/persistence helpers
```

Signal arbitration remains in `services/signal_rules.py`; remote camera transport does not own inference, traffic policy, or signal timing.

## API conventions

Successful JSON:

```json
{"ok": true, "data": {}, "meta": {"request_id": "..."}}
```

Expected errors use central stable error codes/AppError and the standard error envelope. Binary/image/CSV responses preserve `X-Request-ID`.

See `../../../docs/API_CONTRACTS.md`.

## Local backend run

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Use `../../../docs/LOCAL_TESTING.md` for current candidate validation.

## Safety boundary

The backend is a local prototype. Camera input, detections, analytics, simulated signal decisions and experiment outputs are not connected to physical/public-road traffic infrastructure.
