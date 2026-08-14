# Acceptance Checklist — 0_1_2 candidate

Do not mark 0_1_2 as passed until every required checkbox is confirmed by the project owner.

## Required backend and API

- [ ] Backend starts with the documented PowerShell command.
- [ ] `/docs` opens and shows dataset capture plus training endpoints.
- [ ] `/health` returns `ok: true`, version `0_1_2`, and a request ID.
- [ ] `/api/smoke/status` returns version `0_1_2`.
- [ ] `scripts\test_backend_smoke_windows.bat` shows all `PASS`, including dataset/training status.
- [ ] Invalid capture/training input returns the standard error envelope and request ID.

## Required frontend

- [ ] `npm ci`, `npm run typecheck`, and `npm run build` succeed locally.
- [ ] Frontend starts and Dashboard shows `0_1_2`.
- [ ] Sidebar navigation, existing mock Live AI page, logs, and traffic simulation still work.
- [ ] Dataset Capture and Train / Export are shown as test-ready, not as finished production features.

## Required simulation capture

- [ ] Camera simulation starts and shows moving PNG frames.
- [ ] Dataset Capture previews the current simulation frame.
- [ ] **Capture current frame** reports a saved relative path.
- [ ] Images and Metadata each increase by one.
- [ ] A readable PNG exists under `datasets\captures\<session>\images`.
- [ ] A matching JSON exists under `metadata` with `origin: simulation`, tag, note, source, resolution, and relative paths.
- [ ] Counts remain after restarting the backend.

## Required uploaded-frame capture

- [ ] Simulation is stopped and a real JPEG or PNG is uploaded to `/api/camera/frame`.
- [ ] The uploaded image appears in the Camera Sources preview.
- [ ] Capturing it saves the original format and matching metadata with `origin: upload`.

## Required training boundaries

- [ ] Without the optional dependency, the UI explains the install command and `/api/training/start` returns `ATL-TRAIN-001`.
- [ ] Invalid or out-of-project dataset YAML paths are rejected with `ATL-TRAIN-002`.
- [ ] The UI clearly states that raw captures are unlabeled and cannot directly train object detection.
- [ ] The app does not claim that model export, live inference, or physical traffic-light control works.

## Optional end-to-end training check

- [ ] After installing `requirements-training.txt` and supplying a labeled YOLO dataset, one short run starts in the background.
- [ ] Status reaches completed or returns a useful failed state without stopping the API.
- [ ] Training output is written under `outputs\training\<run_id>`.

## Pass decision

Required checks define the 0_1_2 patch pass. The optional end-to-end run confirms the external Ultralytics/PyTorch/data environment and may be deferred if no labeled dataset is available. 0_1_2 remains a candidate until the owner explicitly confirms the required checks.
