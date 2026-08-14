# Local Testing Guide — 0_1_3 candidate

This guide verifies persistent capture, manual bounding-box labeling, managed YOLO dataset generation, and the existing optional local training runner. The project remains a simulation/classroom prototype and is not for real public-road traffic control.

## Requirements

```text
- Python 3.11 or newer recommended
- Node.js 20 or newer recommended
- npm
- optional: a JPEG/PNG test image for receiver testing
- optional: requirements-training.txt for a real Ultralytics run
```

## Start the backend

In PowerShell:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
http://127.0.0.1:8000/api/smoke/status
```

Health and smoke status must report `0_1_3`.

## Start the frontend

In a second PowerShell terminal:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run dev
```

Open `http://localhost:5173`.

## Required capture setup

Create at least two saved frames. Simulation is the simplest path:

1. Open **Camera Sources** and select **Start simulation**.
2. Confirm the image moves.
3. Open **Dataset Capture**.
4. Save one frame under session `label_acceptance` with quality `Useful`.
5. Wait for the simulation scene to move, then save a second frame under the same session.
6. Optionally save a third frame marked `Bad` to verify exclusion behavior.

Confirm the capture files still appear under:

```text
AI_Traffic_Light\datasets\captures\label_acceptance\images
AI_Traffic_Light\datasets\captures\label_acceptance\metadata
```

## Required manual labeling test

1. Open **Dataset Review**.
2. Confirm the captured frames appear in the left browser.
3. Select the first non-bad frame.
4. Choose a class such as `person`.
5. Drag across the image to draw a bounding box.
6. Add a second box with another class if useful.
7. Select **Save labels**.
8. Confirm the page reports saved labels and the selected frame changes to `reviewed`.
9. Select the second non-bad frame.
10. Either draw a box and save, or deliberately save zero boxes to test a reviewed negative example.

On disk, confirm JSON label documents appear under:

```text
AI_Traffic_Light\datasets\captures\label_acceptance\labels
```

Each label JSON must use class IDs/names from the shared schema and record pixel `box_xyxy` coordinates. A saved zero-box document must show `reviewed: true` with an empty `labels` array.

## Required managed YOLO build test

With at least two reviewed non-bad frames:

1. On **Dataset Review**, check the Managed YOLO section reports at least `2` eligible frames.
2. Select **Build training dataset**.
3. Confirm the UI reports at least one train frame and one validation frame.
4. Inspect:

```text
AI_Traffic_Light\datasets\yolo\images\train
AI_Traffic_Light\datasets\yolo\images\val
AI_Traffic_Light\datasets\yolo\labels\train
AI_Traffic_Light\datasets\yolo\labels\val
AI_Traffic_Light\datasets\yolo\data.yaml
AI_Traffic_Light\datasets\yolo\manifest.json
```

Expected:

```text
- train and val each contain at least one image
- every included image has a same-name .txt label file
- reviewed negative frames have an empty .txt label file
- captures marked bad are absent from both splits
- data.yaml lists the six shared classes
- manifest.json records train/val counts and the source signature
```

## Required stale-dataset test

1. Return to a labeled capture in **Dataset Review**.
2. Add, remove, or resize a box by replacing the labels and select **Save labels**.
3. Confirm Managed YOLO status changes to `rebuild required` / stale.
4. Open **Train / Export** with the default `yolo/data.yaml`.
5. Confirm **Start real training** is blocked for the stale managed dataset.
6. Return to **Dataset Review** and rebuild.
7. Confirm status becomes ready/current again.

## Backend scripts

From `AI_Traffic_Light` with the backend environment active:

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

Every script should complete successfully. The smoke payload must include dataset labeling and managed YOLO build endpoints/checks.

## Optional uploaded-frame capture test

Stop simulation, then from a terminal containing a test image:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/camera/frame?source_id=test_camera" -H "Content-Type: image/jpeg" --data-binary "@.\test-frame.jpg"
```

Capture it in **Dataset Capture**, then label it in **Dataset Review**. This confirms receiver-origin images use the same label workflow as simulation captures.

## Optional real YOLO training test

Install the optional training dependency from the backend folder:

```powershell
pip install -r requirements-training.txt
```

Open **Train / Export**. Keep the default:

```text
yolo/data.yaml
```

Use a very small epoch count for acceptance. Expected:

```text
- the start button is enabled only when the managed dataset is current and Ultralytics is available
- one run starts in the background
- the API remains responsive while training runs
- status reaches completed or returns a useful failed state
- outputs appear under AI_Traffic_Light\outputs\training\<run_id>
- best_model_path appears if weights\best.pt is produced
```

A custom labeled YOLO YAML path inside `datasets/` remains supported and is not controlled by the managed-dataset readiness flag.

## Generated-data rule

Do not upload `datasets/`, `outputs/`, `.venv/`, `node_modules/`, or `dist/` to GitHub. They are runtime/generated content and are not part of the changed-files patch.
