# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_2_1` — candidate adding timestamped traffic occupancy analytics, user-defined counting regions, CSV export, history reset, and summary metrics on top of the V020 feature set.
- Previous candidate: `0_2_0`.
- Owner-confirmed passed baseline remains `0_1_7` until V021 is explicitly accepted.

## Implemented prototype functions

- receive or simulate camera frames
- use a controllable synthetic traffic scene with top-to-bottom pedestrians and horizontal vehicle motion
- choose light / normal / busy simulation density and pause/resume an inspection frame
- run a stateful signal-aware junction simulation where vehicles queue at stop lines and pedestrians wait for WALK before using the zebra crossing
- capture and persist dataset images
- delete unwanted captures together with paired metadata and saved manual labels
- manually label frames in the app
- build a managed YOLO dataset
- run local Ultralytics YOLO training
- monitor per-epoch validation fitness / mAP convergence
- stop training automatically when validation fitness stops improving for the configured patience window
- discover, choose, default, and delete local trained models
- run live inference overlays on receiver/simulation frames
- create, edit, persist, and reset traffic-zone polygons directly over the current camera/simulation feed
- overlay saved zones on Live AI with reference-to-frame scaling
- show the exact simulation signal obeyed by synthetic agents as a compact signal at the top-right of Live AI
- count live detection centres inside configured zones
- generate auditable simulation-only traffic phase recommendations from zone counts
- count whole-frame detected pedestrians and vehicles per sampled frame
- define multiple analytics-only counting regions in the existing Zone Editor
- record bounded traffic occupancy history while the backend runs
- plot whole-frame or region-specific pedestrian/vehicle occupancy over selectable time windows
- export traffic history to CSV, clear it explicitly, and inspect average/peak/busiest-region plus phase-change summaries
- persist active runtime settings
- inspect real recent backend logs with request/error metadata
- keep long model IDs and paths contained inside the Live AI model panel

## Development integrity

The root `VERSION` file is the canonical release-state record. Backend version surfaces load it through `apps/pc-studio/backend/app/core/project_version.py` rather than duplicating release strings. Frontend Dashboard/navigation/offline fallback surfaces reuse `apps/pc-studio/frontend/src/constants/projectVersion.ts`, which repository validation checks against root `VERSION`.

Useful developer/agent entry points:

- `AGENTS.md` — mandatory repository rules and release gate
- `docs/AI_AGENT_GUIDE.md` — detailed agent workflow
- `docs/AI_AGENT_CHECKLIST.md` — concise execution checklist
- `docs/CODE_STRUCTURE.md` — module ownership rules
- `docs/DEVELOPMENT_WORKFLOW.md` — current incremental patch workflow
- `docs/LOCAL_TESTING.md` — test commands and evidence expectations
- `docs/TEST_READY_CHECKLIST.md` — owner acceptance checklist
- `docs/VERSIONING.md` — candidate versus passed-baseline rules

Repository/packaging helpers:

```powershell
python .\scripts\check_structure.py
python .\scripts\validate_patch_zip.py <patch.zip>
```

The patch ZIP validator checks structural safety and exclusions. A changed-files-only manifest still needs to be compared against the actual intended source changes.

## Analytics semantics

Traffic history stores **sampled occupancy**: how many detected pedestrians/vehicles are present in each sampled frame or region. It is not a unique passage counter because the current prototype does not assign stable tracking IDs across frames. Runtime history is stored under `outputs/traffic_history/` and is not source-patch content.

## Safety scope

This project is for prototype, classroom, and simulation use only. Zone-aware traffic recommendations, detections, and the Live AI signal graphic are not connected to real public-road traffic infrastructure.
