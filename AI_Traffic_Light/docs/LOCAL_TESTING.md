# Local Testing Guide — 0_1_4 candidate

This guide verifies trained-model discovery and live detection overlay on top of the V013 capture/label/train workflow. The project remains a classroom/prototype traffic-light **simulation** and is not for real public-road signal control.

## Requirements

```text
- Python 3.11 or newer recommended
- Node.js 20 or newer recommended
- npm
- V013 dataset/capture files if you want regression testing
- at least one completed YOLO training run with outputs/training/<run_id>/weights/best.pt
- requirements-training.txt installed for real Ultralytics inference
```

## Start backend

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-training.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/health`. It must report `0_1_4` and a request ID.

## Start frontend

In a second PowerShell terminal:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
npm run dev
```

Open `http://localhost:5173`.

## Confirm a trained model exists

From the project root:

```powershell
Get-ChildItem .\AI_Traffic_Light\outputs\training\*\weights\best.pt | Sort-Object LastWriteTime -Descending | Select-Object LastWriteTime, FullName
```

The newest `best.pt` is what **Load latest trained model** uses. Model weights remain runtime files and are not included in patch ZIPs.

## Required inference API check

With the backend running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/inference/status
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/inference/load-latest
```

Expected status after load:

```text
model_loaded = true
active_model_id = newest training run ID
available_model_count >= 1
active_is_latest = true
backend_available = true
```

If no `best.pt` exists, load-latest should return `ATL-MODEL-003`. If Ultralytics is missing, it should return `ATL-DETECT-001`.

## Required simulation live-overlay test

1. Open **Cameras** and start simulation.
2. Open **Live AI**.
3. V014 should automatically load the newest trained model if no model is already active.
4. Confirm the canvas shows the current simulation image rather than only the old mock SVG scene.
5. Confirm **Trained model** shows `loaded`, the active run ID, and a changing inference latency/frame number.
6. The backend runs at a 10% confidence floor. Move the display confidence slider lower/higher and confirm boxes are hidden/shown without reloading the model.
7. If the model detects an object, confirm its class/confidence box stays aligned with the image while the simulation moves. The frontend uses `/api/inference/frame?source_id=...&frame_number=...`, which addresses the exact recent source image cached for that detection result.
8. Confirm the detection table matches the visible filtered boxes.
9. Select **Unload**. The model state must become `not loaded`, live inference stops, and the app must remain responsive.
10. Select **Load latest trained model** and confirm inference resumes.

A tiny dataset may produce zero useful detections. That is a model-quality limitation, not automatically an API failure. For the overlay acceptance check, use a receiver/simulation frame similar to the labeled training data and lower the display threshold to 10%. At least one returned detection should be visually checked for coordinate alignment.

## Required uploaded-frame alignment test

Stop simulation and upload a static JPEG/PNG using the existing camera endpoint. A static image is useful for checking that class labels and bounding boxes align with the expected object positions without motion between frames.

## Backend regression/unit scripts

From `AI_Traffic_Light` with the backend environment active:

```powershell
python .\scripts\test_camera_frame_service.py
python .\scripts\test_dataset_capture_service.py
python .\scripts\test_dataset_labeling_service.py
python .\scripts\test_training_service.py
python .\scripts\test_inference_service.py
python .\scripts\check_structure.py
```

With the backend running:

```powershell
python .\scripts\test_backend_smoke.py
```

Every test should pass. The smoke script now includes `/api/inference/status` but does not require a trained model to be loaded.

## Boundaries

0_1_4 does not automatically label images, perform live zone counting, feed real detections into traffic decisions, export models, or control physical traffic lights. Traffic decision cards on Live AI remain mock simulation state.
