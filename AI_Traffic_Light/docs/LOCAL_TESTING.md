# Local Testing Guide — 0_1_2 candidate

This guide verifies persistent frame capture and the optional labeled-dataset YOLO runner. The project remains a simulation/classroom prototype and is not for real public-road traffic control.

## Requirements

```text
- Python 3.11 or newer recommended
- Node.js 20 or newer recommended
- npm
- a JPEG/PNG test image for receiver testing
```

## Start the backend

In PowerShell:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/docs`, `/health`, and `/api/smoke/status`. Health and smoke status must report `0_1_2`.

## Start the frontend

In a second PowerShell terminal:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run dev
```

Open `http://localhost:5173`.

## Required simulation capture test

1. Open **Camera Sources** and select **Start simulation**.
2. Confirm the preview moves and receiver status says `image/png` through the API.
3. Open **Dataset Capture**.
4. Enter session ID `sim_acceptance`, select `Useful`, and add a short note.
5. Select **Capture current frame**.
6. Confirm the page reports a saved path and increments both Images and Metadata by one.
7. On disk, open:

```text
AI_Traffic_Light\datasets\captures\sim_acceptance\images
AI_Traffic_Light\datasets\captures\sim_acceptance\metadata
```

There must be one readable PNG and one same-name JSON record. The JSON must show `origin: simulation`, `quality_tag: useful`, the note, resolution, source frame number, and relative paths.

Restart only the backend and revisit **Dataset Capture**. The image/metadata counts must still include the saved pair.

## Required uploaded-frame capture test

Stop simulation, then run this from a PowerShell terminal containing a real test image:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/camera/frame?source_id=test_camera" -H "Content-Type: image/jpeg" --data-binary "@.\test-frame.jpg"
```

Confirm the uploaded image appears on **Camera Sources**. Capture it under session `receiver_acceptance`, then verify a readable JPEG and matching JSON with `origin: upload`.

## Backend scripts

From `AI_Traffic_Light` with the backend environment active:

```powershell
python .\scripts\test_camera_frame_service.py
python .\scripts\test_dataset_capture_service.py
python .\scripts\test_training_service.py
python .\scripts\check_structure.py
```

With the backend running:

```powershell
python .\scripts\test_backend_smoke.py
```

Every line must show `PASS`, and the smoke script must include dataset and training status.

## Optional real YOLO training test

Training is not part of the lightweight backend install. From the backend folder:

```powershell
pip install -r requirements-training.txt
```

Prepare a labeled YOLO detection dataset and YAML under `AI_Traffic_Light\datasets\`, then open **Train / Export**. Enter the YAML path relative to `datasets`, keep `device` as `cpu` unless the installed PyTorch backend supports another device, and start a short run.

Expected:

```text
- only one run starts
- status changes from running to completed or a useful failed state
- progress updates between epochs when supported by the installed Ultralytics version
- outputs appear under AI_Traffic_Light\outputs\training\<run_id>
- best_model_path appears if weights\best.pt is produced
```

Raw files under `datasets\captures` are not labeled and are rejected as a training substitute. The runner does not implement cancellation, automatic labeling, or model export. Restarting the backend interrupts an active run and resets the in-memory run status, while already written output files remain on disk.

## Generated-data rule

Do not upload `datasets/`, `outputs/`, `.venv/`, `node_modules/`, or `dist/` to GitHub. They are runtime/generated content and are not part of the changed-files patch.
