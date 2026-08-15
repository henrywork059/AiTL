# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_2_2` — candidate adding cross-frame object IDs, directional counting lines, unique passage events, region entry/exit/dwell analytics, and persistent flow-event history on top of V021.
- Previous candidate: `0_2_1`.
- Owner-confirmed passed baseline remains `0_1_7` until a newer candidate is explicitly accepted.

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
- run live inference overlays on receiver/simulation frames and assign prototype track IDs across consecutive frames
- create, edit, persist, and reset traffic-zone polygons directly over the current camera/simulation feed
- overlay saved zones on Live AI with reference-to-frame scaling
- show the exact simulation signal obeyed by synthetic agents as a compact signal at the top-right of Live AI
- count live detection centres inside configured zones
- generate auditable simulation-only traffic phase recommendations from zone counts
- count whole-frame detected pedestrians and vehicles per sampled frame
- define multiple analytics-only counting regions and two-point counting lines in the existing Zone Editor
- record bounded traffic occupancy history while the backend runs
- plot whole-frame or region-specific pedestrian/vehicle occupancy over selectable time windows
- export occupancy history to CSV, clear it explicitly, and inspect average/peak/busiest-region plus phase-change summaries
- record unique directional passage events when a stable track crosses a counting line
- record region entry/exit and completed dwell duration, including pedestrian waiting-zone dwell
- persist/filter/plot/export track-derived flow events separately from sampled occupancy
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

V022 keeps two metrics deliberately separate:

- **Occupancy** — V021-style sampled counts showing how many detections are present in a frame/region at a point in time. Runtime data is stored under `outputs/traffic_history/`.
- **Flow** — V022 track-derived events. A unique passage is counted only when one stable prototype track crosses one configured `counting_line`; region entry/exit and dwell are separate event types stored under `outputs/traffic_flow/`.

The tracker uses lightweight class-aware centroid/IoU matching. Heavy occlusion or crowded same-class motion can still lose/swap IDs, so flow remains prototype analytics rather than certified traffic measurement. Both runtime directories are excluded from source patches.

## Safety scope

This project is for prototype, classroom, and simulation use only. Zone-aware traffic recommendations, detections, and the Live AI signal graphic are not connected to real public-road traffic infrastructure.
