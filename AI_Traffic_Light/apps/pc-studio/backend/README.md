# PC Studio Backend

Python/FastAPI backend for the AI Traffic Light PC Studio App.

## Current state — 0_1_2

This backend is a **persistent capture candidate with a camera receiver, PNG simulation, mock AI APIs, and an optional YOLO training runner**.

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
- save receiver or simulation images with paired JSON metadata
- count captures across backend restarts
- validate and launch optional labeled-dataset YOLO training
```

It cannot yet:

```text
- open a real camera
- run ESP32/Raspberry Pi camera firmware
- run YOLO inference
- train from raw unlabeled captures
- export models
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
http://127.0.0.1:8000/api/dataset/status
http://127.0.0.1:8000/api/training/status
```

Captured files are saved under the project `datasets/captures/` folder. To enable real YOLO training after preparing labels and `datasets/<name>/data.yaml`, run `pip install -r requirements-training.txt` from this backend folder. Training outputs go to `outputs/training/`.

## Smoke test

From the project root, with backend running:

```bash
python scripts/test_backend_smoke.py
```
