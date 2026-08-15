# Local Testing Notes (V021)

V021 / `0_2_1` is the current candidate, explicitly requested as the next patch after V020 / `0_2_0`. The owner-confirmed passed baseline remains V017 / `0_1_7`. Automated checks do not promote V021.

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
python .\scripts\test_traffic_history_service.py
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

The smoke script also checks:

- standard `ok` envelopes;
- `meta.request_id` on JSON endpoints;
- `/health`, `/api/smoke/status`, and `/api/template/pc-studio` all report the root `VERSION` value;
- the traffic-history JSON endpoint responds;
- the CSV export has the expected header and `X-Request-ID`.

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

## 8. Key V021 manual checks

1. Dashboard and visible version surfaces report `0_2_1` with the traffic-analytics candidate wording.
2. `/health`, `/api/smoke/status`, and `/api/template/pc-studio` report `0_2_1` consistently.
3. Start simulation or upload a device frame and load a trained model. Confirm Traffic Logic shows whole-frame pedestrian/vehicle totals.
4. In Zone Editor, create and save at least two `counting_region` polygons over different areas. Navigate away/back and confirm they persist.
5. Confirm Traffic Logic shows separate pedestrian/vehicle/total occupancy for the configured regions while the existing simulation recommendation still depends only on waiting/crossing/queue logic.
6. Leave the backend/model/simulation running for at least 20-30 seconds, open Traffic Analytics, and confirm timestamped points accumulate rather than duplicating one source frame.
7. Switch Analytics between Whole frame and each counting region; confirm the chart and current/average/peak metrics change with the selected scope.
8. Change time windows and confirm the number/range of plotted samples changes appropriately.
9. Confirm busiest-region and phase-change summaries render when enough data exists.
10. Export CSV and confirm the selected scope/time window is represented and the file contains timestamp/frame/count/phase/decision columns.
11. Use Clear history after confirmation and verify the stored history is reset while captures, labels, zones, trained models, and settings remain intact. If valid inference continues, new samples may begin appearing again on the next recorder interval.
12. Confirm the UI/documentation describes counts as sampled occupancy, not unique passage/throughput.
13. Recheck original V020 camera-backed Zone Editor, Live AI saved-zone overlay, **Show zones**, compact simulated signal, and capture deletion lifecycle.
14. Recheck V017 training convergence/early stopping, Settings, Logs, model selection/default/delete, confidence controls, simulation density/pause, capture, labeling, and training.
15. Confirm no feature controls physical public-road traffic infrastructure.

Only the owner can mark V021 passed after the required manual checks.
