# PC Studio Backend

Python/FastAPI backend for the AI Traffic Light PC Studio App.

## Current state — 0_1_3

This backend is a **manual-labeling candidate** built on the existing camera receiver, simulation, persistent capture, mock APIs, and optional YOLO training runner.

It can:

```text
- start with Uvicorn
- return health and smoke-test status
- return standard API envelopes, request IDs, logs, and stable error codes
- accept raw JPEG/PNG camera frames
- generate synthetic moving PNG frames for hardware-free testing
- save receiver or simulation images with paired JSON metadata
- browse persistent captures across backend restarts
- save manual bounding-box labels using the shared six-class schema
- save reviewed zero-box negative examples
- exclude bad-quality captures from managed training builds
- build a deterministic YOLO train/validation dataset at datasets/yolo/
- detect when saved labels make the managed YOLO dataset stale
- validate and launch optional labeled-dataset Ultralytics YOLO training
```

It cannot yet:

```text
- open a real webcam directly
- run ESP32/Raspberry Pi camera firmware
- automatically label captured objects
- run YOLO inference in the live view
- export models
- control physical public traffic lights
```

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Useful endpoints:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
http://127.0.0.1:8000/api/smoke/status
http://127.0.0.1:8000/api/dataset/status
http://127.0.0.1:8000/api/dataset/captures
http://127.0.0.1:8000/api/dataset/training-dataset/status
http://127.0.0.1:8000/api/training/status
```

Capture images/metadata/labels are stored under `datasets/captures/`. The managed dataset builder writes `datasets/yolo/data.yaml`, train/validation images, YOLO `.txt` labels, and a manifest. All generated dataset/output folders stay out of patch ZIPs.

To enable the real optional YOLO training runner:

```powershell
pip install -r requirements-training.txt
```

Training outputs go to `outputs/training/`.

## Tests

From the `AI_Traffic_Light` root with the backend environment active:

```powershell
python .\scripts\test_camera_frame_service.py
python .\scripts\test_dataset_capture_service.py
python .\scripts\test_dataset_labeling_service.py
python .\scripts\test_training_service.py
python .\scripts\check_structure.py
```

With the backend running:

```powershell
python .\scripts\test_backend_smoke.py
```
