# Local Testing Notes (V020)

V020 / `0_2_0` remains a candidate. The owner-confirmed passed baseline is V017 / `0_1_7`. This maintenance hardening does not promote V020.

## 1. Use the backend virtual environment

From the backend directory:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-training.txt
```

Then return to `AI_Traffic_Light` for project scripts:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
```

If needed, call the interpreter explicitly from the repository root:

```powershell
.\AI_Traffic_Light\apps\pc-studio\backend\.venv\Scripts\python.exe <script>
```

## 2. Compile and repository consistency checks

```powershell
python -m compileall .\apps\pc-studio\backend\app .\scripts
python .\scripts\check_structure.py
```

`check_structure.py` now validates required project/agent docs, required `VERSION` fields, current patch/changelog presence, backend single-source version usage, the shared frontend project-version mirror, and that known frontend version surfaces import it instead of repeating release literals.

## 3. Automated backend/service checks

Run the existing V020/V017 regression scripts:

```powershell
python .\scripts\test_camera_frame_service.py
python .\scripts\test_camera_simulation_api.py
python .\scripts\test_dataset_capture_delete.py
python .\scripts\test_training_service.py
python .\scripts\test_zone_traffic_services.py
python .\scripts\test_runtime_settings_logs.py
python .\scripts\test_prototype_tools_api.py
```

Run any additional focused test script related to files changed by a later patch.

## 4. Live backend API smoke check

Start the backend:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another PowerShell, with the backend `.venv` active, run from `AI_Traffic_Light`:

```powershell
python .\scripts\test_backend_smoke.py
```

The smoke script now also checks:

- standard `ok` envelopes;
- `meta.request_id` on JSON endpoints;
- `/health`, `/api/smoke/status`, and `/api/template/pc-studio` all report the root `VERSION` value.

## 5. Frontend validation

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
npm run dev
```

Open `http://localhost:5173/`.

## 6. Git/change hygiene

From the complete Git repository:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git diff --check
```

Review the actual changed-file list. Do not treat untracked `datasets/`, `outputs/`, trained models, labels, or runtime files as disposable source clutter.

For stale-version checking, focus on runtime/current-state surfaces. Historical changelog and old patch documents are expected to contain old version strings.

## 7. Patch ZIP validation

After creating the changed-files-only patch:

```powershell
python .\scripts\validate_patch_zip.py <path-to-patch.zip>
```

The validator rejects files outside `AI_Traffic_Light/`, path traversal, ZIP corruption, and forbidden runtime/generated paths such as datasets, outputs, models, virtual environments, dependencies/builds, caches, and bytecode.

It cannot prove that every included file actually changed. Compare the ZIP manifest against `git diff --name-only` or the intended changed-file manifest separately.

## 8. Key V020 manual checks

1. Dashboard and visible version surfaces report `0_2_0`.
2. `/health`, `/api/smoke/status`, and `/api/template/pc-studio` report `0_2_0` consistently.
3. Start simulation or upload a device frame, then open Zone Editor; the current camera frame is the editor background.
4. Draw/edit/save a zone over a visible feature. Navigate away and back and confirm geometry persists.
5. Open Live AI and confirm the same saved zones are overlaid on the live camera image.
6. Toggle **Show zones** off/on and confirm only zone graphics change; detections continue normally.
7. Confirm a compact traffic signal is visible at the top-right of the Live AI image and changes with the simulation-only traffic phase.
8. Capture an image, then delete it from Dataset Capture; counts and last-capture state update.
9. Capture another image, save manual labels, delete it in Dataset Review, and confirm image/metadata/labels disappear.
10. If the deleted item was used in a managed YOLO build, confirm the UI reports that the managed dataset requires rebuilding.
11. Recheck V017 training convergence/early stopping, Settings, Logs, Traffic Logic, model selection/default/delete, confidence controls, simulation density/pause, capture, labeling, and training.
12. Confirm no feature controls physical public-road traffic infrastructure.

Only the owner can mark V020 passed after the required manual checks.
