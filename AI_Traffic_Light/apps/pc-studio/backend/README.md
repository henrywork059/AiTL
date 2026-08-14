# PC Studio Backend

Python/FastAPI backend for the AI Traffic Light PC Studio App.

## Current state — 0_1_1

This backend is **test-ready with a camera-frame receiver, simulation, and mock AI APIs**.

It can:

```text
- start with Uvicorn
- return health status
- return smoke-test status
- return mock detection frames
- return mock traffic zones
- return mock traffic-light state
- return mock logs
- return standard API envelopes and error codes
- accept raw JPEG/PNG camera frames
- return the latest frame and receiver metadata
- generate synthetic moving frames for hardware-free testing
```

It cannot yet:

```text
- open a real camera
- run ESP32/Raspberry Pi camera firmware
- run YOLO inference
- train/export models
- control physical traffic lights
```

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
http://127.0.0.1:8000/api/smoke/status
http://127.0.0.1:8000/api/camera/status
```

## Smoke test

From the project root, with backend running:

```bash
python scripts/test_backend_smoke.py
```
