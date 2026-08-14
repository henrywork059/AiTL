# Acceptance Checklist — 0_1_4 candidate

Do not mark 0_1_4 as passed until the project owner confirms every required check.

## Backend and build

- [ ] `AI_Traffic_Light\VERSION` reports `0_1_4` and still identifies the prior passed baseline correctly.
- [ ] Backend starts with the documented PowerShell command.
- [ ] `/health` returns `ok: true`, version `0_1_4`, and a request ID.
- [ ] `/api/smoke/status` returns version `0_1_4` and includes trained-model inference in the test-ready list.
- [ ] `python .\scripts\test_inference_service.py` shows every line as `PASS`.
- [ ] Existing camera, capture, labeling, training, structure, and backend smoke tests still pass.
- [ ] Frontend `npm ci`, `npm run typecheck`, and `npm run build` succeed.

## Trained-model discovery/load

- [ ] At least one `outputs\training\<run_id>\weights\best.pt` exists locally.
- [ ] `/api/inference/status` reports at least one available model.
- [ ] **Live AI** automatically loads the newest model when opened, or **Load latest trained model** loads it manually.
- [ ] The shown active run ID/path corresponds to the newest `best.pt`.
- [ ] Restarting the backend does not lose model discovery; reopening Live AI can load the existing trained file again.

## Live receiver/simulation inference

- [ ] Start camera simulation and confirm Live AI shows the real simulation image.
- [ ] Inference frame number and latency update while frames change.
- [ ] The backend remains responsive while inference polling runs.
- [ ] Detection table is populated when the trained model returns detections.
- [ ] Lowering/raising the display confidence threshold filters visible boxes and table rows.
- [ ] For at least one detection on a training-like frame, the box/class/confidence visually align with the object.
- [ ] `/api/inference/frame?source_id=...&frame_number=...` displays the exact inferred source frame and does not visibly drift one simulation frame ahead of the boxes.

## Model controls/errors

- [ ] **Unload** clears the active model without crashing the backend/frontend.
- [ ] After unload, direct `/api/inference/detections` returns the standard error envelope with `ATL-DETECT-001` and a request ID.
- [ ] **Load latest trained model** restores inference after unload.
- [ ] A missing trained `best.pt` is handled with `ATL-MODEL-003`, not an anonymous exception.

## V013 regression and safety

- [ ] Dataset Capture still saves receiver/simulation frames.
- [ ] Dataset Review still loads/saves manual labels and builds `yolo/data.yaml`.
- [ ] Train / Export still starts a valid local training run when prerequisites are met.
- [ ] Live detections do **not** automatically control zone counts or physical traffic signals.
- [ ] The UI/docs still describe the project as prototype/simulation scope.

## Pass decision

0_1_4 remains a candidate until the owner explicitly confirms the required checks. Detection accuracy is dataset/model dependent, but at least one returned detection must be visually checked for correct overlay coordinates when a suitable frame produces a detection.
