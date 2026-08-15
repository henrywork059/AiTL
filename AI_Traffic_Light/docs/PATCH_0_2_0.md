# Patch 0_2_0 — Camera-aligned zones, capture lifecycle, and maintenance hardening

## Baseline and version

- Current candidate: V020 / `0_2_0`.
- Previous version: `0_1_7`.
- Passed baseline: `0_1_7` (owner-confirmed before V020).
- This maintenance revision does **not** mark V020 passed and does not create a new release number.

## Implemented V020 feature changes

### Capture deletion

- Added `DELETE /api/dataset/captures/{capture_id}`.
- Dataset Capture can delete the latest capture.
- Dataset Review can delete the selected capture.
- Deletion removes the raw image, paired metadata, and optional manual-label document.
- Removal is staged through same-filesystem renames before final cleanup to reduce partial-delete risk.
- Managed YOLO dataset status is returned after deletion so a previous build can be marked stale.
- Added stable `ATL-DATASET-007` for deletion failures.

### Camera-aligned Zone Editor

- Zone Editor uses the current `/api/camera/frame` receiver/simulation image as its background.
- Camera status is polled while Zone Editor is active.
- The camera image maps into the existing validated 1280×720 zone reference coordinates, preserving the traffic-counting contract.

### Live AI zone overlay

- Persisted zone polygons scale from 1280×720 reference coordinates into the active camera/detection frame resolution.
- Live AI includes a **Show zones** visibility toggle.
- Zone overlays and YOLO boxes share the displayed camera frame coordinate context.

### Compact simulated traffic signal

- Live AI shows a small traffic signal in the top-right corner of the image.
- It reflects the current simulation-only phase.
- It is visualization only and is not connected to real traffic hardware.

## Maintenance hardening in this revision

### Single-source backend release metadata

- Added `app/core/project_version.py` to parse and validate root `VERSION`.
- FastAPI app metadata, `/health`, smoke status, and template status now read the project version from that shared source.
- The shared module fails clearly if required `VERSION` fields are missing or malformed, reducing silent stale-version drift.
- Centralized the current backend mode string with the release metadata helper so health/smoke/template do not repeat it.
- Added shared frontend `src/constants/projectVersion.ts`; Dashboard, API fallbacks, and navigation now import the shared value rather than repeating `0_2_0`.

### Stronger validation tooling

- Upgraded `scripts/check_structure.py` from a skeleton-file check to repository/version consistency validation.
- It checks required current docs/files, required `VERSION` fields, candidate/baseline consistency, current patch/changelog presence, backend version-source usage, and that the shared frontend version mirror matches root `VERSION` while known frontend surfaces avoid release literals.
- Upgraded `scripts/test_backend_smoke.py` to require `meta.request_id` and verify health/smoke/template versions agree with root `VERSION`.
- Added `scripts/validate_patch_zip.py` to reject unsafe paths, forbidden runtime/generated content, corrupt ZIPs, and members outside `AI_Traffic_Light/`.

### AI-agent/developer instructions

- Reworked `AGENTS.md` into a strict read-order, version gate, architecture, data-safety, testing-evidence, packaging, and local-update protocol.
- Reworked `docs/AI_AGENT_GUIDE.md`, `docs/CODE_STRUCTURE.md`, `docs/DEVELOPMENT_WORKFLOW.md`, and `docs/VERSIONING.md` around the current V020 architecture rather than the old skeleton workflow.
- Added `docs/AI_AGENT_CHECKLIST.md` as a concise execution checklist for future agents.
- Updated testing/function docs to make owner acceptance distinct from automated test readiness.

## API/error compatibility

This maintenance revision adds no new endpoint and changes no documented response shape or stable error code. Existing V020 API contracts remain in effect.

## Functional compatibility

V017 convergence monitoring, patience-based early stopping, persistent settings/logs, persistent zones, live zone counting, Traffic Logic, capture/label/train, Model Registry, live inference, and V020 camera-aligned zone/capture-deletion behavior remain in scope without intentional functional changes.

## Validation focus

Run:

- Python compile checks;
- `scripts/check_structure.py`;
- existing camera/dataset/training/zone/settings/API regression scripts;
- `scripts/test_backend_smoke.py` with the backend running;
- frontend typecheck/build;
- `git diff --check` in the complete repository;
- `scripts/validate_patch_zip.py` on the final patch ZIP;
- the manual V020 checklist in `docs/TEST_READY_CHECKLIST.md`.

V020 remains a candidate until owner acceptance.
