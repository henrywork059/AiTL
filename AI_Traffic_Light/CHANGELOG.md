# Changelog

## 0_1_0 — PC Studio test-ready mock version

- Promoted the PC Studio template from layout-only to a local smoke-testable mock version.
- Added backend smoke-test endpoints and backend self-check script.
- Added frontend/backend status display, refresh flow, and mock API integration checks.
- Updated visible version labels from 0_0_4 to 0_1_0.
- Added human testing instructions and a test-ready checklist.
- Still intentionally excludes real YOLO inference, real camera capture, training, model export, and physical traffic-light control.

## 0_0_4 — PC Studio app template and function map

- Added the first structured PC Studio frontend template.
- Added sidebar navigation and placeholder pages for all planned main functions.
- Added reusable layout, placeholder, metric, checklist, and status components.
- Added central frontend page and function registries.
- Added backend placeholder route modules for camera, inference, zones, dataset, training, model registry, settings, logs, and template metadata.
- Updated backend app wiring to expose the placeholder API structure.
- Expanded error-code ranges for future camera, inference, zone, dataset, training, model, settings, and logging work.
- Added human/AI documentation for confirming the PC Studio function list and GUI layout before real implementation.

## 0_0_3 — Modular code, API contracts, logging, and error codes

- Added coding standards for small, debuggable modules.
- Added backend logging/error-code infrastructure.
- Added API response envelope helpers and exception handling.
- Added frontend API/debug logging helpers.
- Refactored placeholder backend routes into smaller route/core/service modules.
- Added documentation for API contracts, debugging, logging, and error-code ranges.
- Added patch notes for **0_0_3**.

## 0_0_2 — Human and AI-agent instruction docs

- Added root-level `AGENTS.md` for AI agents and coding assistants.
- Added `docs/AI_AGENT_GUIDE.md` with detailed project rules for AI agents.
- Added `docs/HUMAN_GUIDE.md` with human-facing usage, upload, patch, and safety instructions.
- Updated README documentation links.
- Updated version metadata to **0_0_2**.

## 0_0_1 — Documentation and version cleanup

- Corrected project wording from the earlier “Version 1 / 0.1.0” draft to the chosen **0_0_x** versioning scheme.
- Updated README layout references from `AI_Traffic_Light_v1/` to `AI_Traffic_Light/`.
- Added clear baseline/patch distinction:
  - `0_0_0` = initial skeleton.
  - `0_0_1` = documentation/version cleanup.
- Updated documentation roadmap and versioning notes.
- Updated placeholder UI/backend version labels to avoid old version naming.

## 0_0_0 — Initial starter skeleton

- Added monorepo project structure.
- Added PC Studio backend placeholder.
- Added PC Studio frontend placeholder GUI.
- Added ESP32-CAM firmware placeholder.
- Added shared schemas.
- Added documentation and roadmap.
- Added sample fake detection data.
- Added Windows helper scripts.
