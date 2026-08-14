# Patch 0_1_2 — Persistent capture and optional YOLO training

## Purpose

Make Dataset Capture functional without replacing the 0_1_1 camera architecture. The same capture action now saves either an uploaded device frame or a synthetic simulation frame.

## Implemented workflow

1. Start the backend and frontend.
2. Upload a JPEG/PNG or start camera simulation.
3. Open **Dataset Capture**.
4. Choose a session ID, quality tag, and optional note.
5. Select **Capture current frame**.
6. Confirm one image under `datasets/captures/<session>/images/` and one matching JSON record under `metadata/`.
7. Restart the backend and confirm the capture counts remain.

Simulation now produces PNG bytes, so simulated and device images pass through the same persistent writer.

## Optional real training

The Train / Export page can launch a real background Ultralytics YOLO run after:

```powershell
cd .\apps\pc-studio\backend
pip install -r requirements-training.txt
```

Prepare a labeled YOLO dataset and YAML under `datasets/`, for example `datasets/yolo/data.yaml`. Raw captured images do not contain bounding-box labels and cannot be trained directly.

The runner validates project-relative paths and basic YOLO YAML keys, permits one active job, reports progress/status, and writes results to `outputs/training/`. Run state is held in memory, and restarting the backend interrupts an active run. Training cancellation, automatic labeling, evaluation UI, and export are not implemented in this patch.

## Safety and data boundaries

- `datasets/` and `outputs/` are generated, Git-ignored, and excluded from the patch.
- Captured images may contain personal data; collect and retain them only with appropriate permission.
- This remains a traffic-light simulation and classroom prototype. It does not control real public-road signals.
- 0_1_2 is a candidate until the owner completes every acceptance check.
