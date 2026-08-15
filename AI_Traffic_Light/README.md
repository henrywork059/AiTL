# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_2_0` — capture deletion, camera-aligned zones, Live AI zone overlays/compact signal display, plus maintenance hardening for version consistency, validation, and AI-agent guidance.
- Passed baseline remains `0_1_7` until the owner explicitly accepts V020.

## Implemented prototype functions

- receive or simulate camera frames
- use a controllable synthetic traffic scene with top-to-bottom pedestrians and horizontal vehicle motion
- choose light / normal / busy simulation density and pause/resume an inspection frame
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
- show the simulation-only traffic phase as a compact signal at the top-right of Live AI
- count live detection centres inside configured zones
- generate auditable simulation-only traffic phase recommendations from zone counts
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

## Safety scope

This project is for prototype, classroom, and simulation use only. Zone-aware traffic recommendations, detections, and the Live AI signal graphic are not connected to real public-road traffic infrastructure.
