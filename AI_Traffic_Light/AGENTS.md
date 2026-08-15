# AGENTS.md — AI Agent Working Rules

This file gives short mandatory instructions for AI agents, coding assistants, and automation tools working on this repository.

For deeper guidance, read:

```text
docs/AI_AGENT_GUIDE.md
docs/CODE_STRUCTURE.md
docs/API_CONTRACTS.md
docs/ERROR_CODES.md
docs/DEBUGGING_AND_LOGGING.md
```

## Project identity

Project name: **AI Traffic Light**
Current patch line: **0_1_x**
Current patch: **0_1_7**

This is a student-scale AI vision traffic-light prototype. It is for simulation, demonstration, data capture, supervised labeling, local trained-model inference, and controlled testing. It must not be described or modified as a ready-to-deploy public-road traffic signal controller.

## Architecture rule

Keep the project split into these parts:

```text
apps/pc-studio/        PC app: GUI, detection, training, evaluation, export, dataset capture
apps/device-camera/    Camera node: ESP32-CAM or similar frame sender only
packages/schema/       Shared schemas and data contracts
packages/ui/           Shared UI/component planning
```

The PC does heavy AI work. The ESP/device camera captures frames and sends them to the PC. Do not move training or heavy segmentation inference onto the ESP camera.

## Code modularity rule

Break code into small files with single responsibilities.

Required backend layering:

```text
app/main.py       app factory, middleware, router registration only
app/routes/       thin HTTP/API handlers only
app/services/     business logic: detection, counting, traffic decisions, data capture
app/core/         logging, error codes, exceptions, API response helpers
app/models.py     Pydantic request/response models only
```

Required frontend layering:

```text
src/App.tsx             page composition only
src/components/         small display/control components
src/lib/apiClient.ts    API fetch wrapper
src/lib/logger.ts       frontend logging helper
src/lib/errorCodes.ts   frontend error-code constants
src/types.ts            shared frontend types
```

Do not place camera capture, AI inference, zone counting, traffic decisions, file I/O, and UI rendering in one large file.

## API rule

Use documented API contracts. For new backend endpoints, prefer this envelope shape:

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "request_id": "..."
  }
}
```

Errors should use:

```json
{
  "ok": false,
  "error": {
    "code": "ATL-AREA-NNN",
    "message": "Human-readable message",
    "details": {}
  },
  "meta": {
    "request_id": "..."
  }
}
```

Binary image endpoints should still return an `X-Request-ID` header.

## Logging and error-code rule

Most non-trivial code should log useful events and failures.

Use central error codes from:

```text
apps/pc-studio/backend/app/core/error_codes.py
docs/ERROR_CODES.md
```

Do not raise anonymous exceptions for expected project errors. Use `AppError` where possible.

## Safety rule

Do not add instructions for controlling real public traffic lights. Use language such as:

```text
traffic-light simulation
model junction
LED demo
prototype controller
human-supervised decision support
```

Avoid claiming:

```text
road-ready
certified
safe for public deployment
automatically controls real traffic infrastructure
```

## Versioning rule

Use the underscore version style requested by the project owner:

```text
0_0_0 = initial skeleton
0_0_1 = documentation/version cleanup
0_0_2 = human and AI-agent instruction docs
0_0_3 = modular code, API, logging, and error-code standards
```

For patch zips, include **only changed files** with the same relative paths. Do not package the whole repository unless explicitly requested.

## Editing rule

Make the smallest useful change. Do not rewrite unrelated files. Do not rename folders unless the user explicitly asks.

When adding or modifying behavior, update at least one of:

```text
README.md
CHANGELOG.md
VERSION
docs/PATCH_<version>.md
relevant docs/*.md
```

## Dataset and labeling rule

- Captured images, manual labels, generated YOLO splits, and trained weights are runtime data and must stay out of patch ZIPs.
- Keep class IDs aligned with `packages/schema/classes.default.json` unless an explicit schema migration is approved.
- Manual labels are human annotations; do not describe them as automatic AI labels.
- A reviewed frame with zero boxes is a valid negative example; an unreviewed frame is not equivalent to a negative label.
- Frames tagged `bad` should not be included in managed training builds.

## Trained-model inference rule

- Trained `best.pt` files remain runtime output under `outputs/training/`; never package model weights into code patches.
- Prefer loading trained models on the PC only. Device-camera firmware remains frame capture/sender logic.
- Live inference results must preserve original camera coordinates so overlays and later zone counting are auditable.
- Do not silently connect live detections to physical traffic-light control. Current live inference is visualization/test input for later simulation logic only.

## Data and secrets rule

Do not commit:

```text
API keys
passwords
Wi-Fi credentials
private camera IPs if sensitive
large datasets
large trained model files
personal data from real pedestrians or vehicles
```

Use placeholders and `.gitkeep` files for folders that will later contain large/private data.


## Current candidate note
- Current candidate patch in this workspace: 0_1_7 (training convergence, automatic early stopping, and working prototype tools).
