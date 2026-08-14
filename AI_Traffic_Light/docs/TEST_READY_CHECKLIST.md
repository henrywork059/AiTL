# Acceptance Checklist — 0_1_3 candidate

Do not mark 0_1_3 as passed until every required checkbox is confirmed by the project owner.

## Required backend and version checks

- [ ] Backend starts with the documented PowerShell command.
- [ ] `/docs` opens and shows capture, label, managed-dataset, and training endpoints.
- [ ] `/health` returns `ok: true`, version `0_1_3`, and a request ID.
- [ ] `/api/smoke/status` returns version `0_1_3` and includes dataset labeling/build checks.
- [ ] `python .\scripts\test_dataset_labeling_service.py` shows all `PASS` lines.
- [ ] Existing camera capture and training service tests still pass.
- [ ] Invalid label coordinates/class IDs return a standard error envelope using `ATL-DATASET-004` or request validation using `ATL-API-002`.
- [ ] Trying to build with fewer than two eligible reviewed frames returns `ATL-DATASET-005`.

## Required frontend checks

- [ ] `npm ci`, `npm run typecheck`, and `npm run build` succeed locally.
- [ ] Frontend starts and the sidebar/dashboard show `0_1_3`.
- [ ] Existing Camera Sources, Dataset Capture, mock Live AI, traffic simulation, and logs still open normally.
- [ ] Dataset Review is shown as test-ready and contains the capture browser, class selector, image canvas, label list, and managed-dataset section.
- [ ] The app does not describe manual labels as automatic AI labels.

## Required manual labeling checks

- [ ] At least two non-bad captures appear in Dataset Review.
- [ ] Selecting a capture loads the correct saved image.
- [ ] Drawing a box creates a visible box with the selected class name.
- [ ] Switching classes allows a different class to be added.
- [ ] **Remove** removes only the selected local label.
- [ ] **Save labels** persists the boxes and marks the capture reviewed.
- [ ] Refreshing the page/backend reloads the saved labels from disk.
- [ ] A corresponding JSON file exists under `datasets\captures\<session>\labels\`.
- [ ] Saving zero boxes creates a reviewed negative example rather than returning the frame to unreviewed state.
- [ ] A capture marked `bad` can be reviewed but is reported as excluded from the managed training build.

## Required managed YOLO dataset checks

- [ ] **Build training dataset** is disabled until at least two non-bad reviewed frames exist.
- [ ] Building creates `datasets\yolo\data.yaml` and `manifest.json`.
- [ ] Building creates both `images\train` and `images\val` with at least one image each.
- [ ] Building creates matching `labels\train` and `labels\val` `.txt` files.
- [ ] YOLO label rows use normalized values between 0 and 1 and the correct class ID.
- [ ] A reviewed negative image receives an empty `.txt` label file.
- [ ] A capture tagged `bad` is not copied into train or val.
- [ ] `data.yaml` lists person, car, bus, truck, motorcycle, and bicycle using IDs 0–5.
- [ ] Editing/saving labels after a build marks the managed dataset stale/rebuild-required.
- [ ] Rebuilding clears stale state and updates train/val status.

## Required training integration boundaries

- [ ] **Train / Export** defaults to `yolo/data.yaml`.
- [ ] With `yolo/data.yaml`, training is blocked until the managed dataset is current.
- [ ] With the optional dependency absent, the UI still explains `pip install -r requirements-training.txt` and no training job starts.
- [ ] A custom labeled YOLO YAML inside `datasets/` remains accepted by the existing training API rules.
- [ ] The app does not claim that live inference, automatic labeling, model export, or physical public-road traffic-light control works.

## Optional end-to-end Ultralytics check

- [ ] Install `requirements-training.txt`.
- [ ] Start a short run using the generated `yolo/data.yaml`.
- [ ] Status reaches completed or returns a useful failed state without stopping the API.
- [ ] Training output is written under `outputs\training\<run_id>`.
- [ ] `best_model_path` appears if Ultralytics produces `weights\best.pt`.

## Pass decision

The required checks define the 0_1_3 patch pass. The optional Ultralytics run depends on the local PyTorch/Ultralytics environment and may be deferred only if that external training environment is unavailable. **0_1_3 remains a candidate until the owner explicitly confirms the required checks.**
