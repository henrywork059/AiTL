# AGENTS.md — AI Agent Working Rules

This file gives short mandatory instructions for AI agents, coding assistants, and automation tools working on this repository.

For deeper guidance, read `docs/AI_AGENT_GUIDE.md`.

## Project identity

Project name: **AI Traffic Light**  
Current patch line: **0_0_x**  
Current patch: **0_0_2**

This is a student-scale AI vision traffic-light prototype. It is for simulation, demonstration, data capture, and controlled testing. It must not be described or modified as a ready-to-deploy public-road traffic signal controller.

## Architecture rule

Keep the project split into these parts:

```text
apps/pc-studio/        PC app: GUI, detection, training, evaluation, export, dataset capture
apps/device-camera/    Camera node: ESP32-CAM or similar frame sender only
packages/schema/       Shared schemas and data contracts
packages/ui/           Shared UI/component planning
```

The PC does heavy AI work. The ESP/device camera captures frames and sends them to the PC. Do not move training or heavy segmentation inference onto the ESP camera.

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
0_0_3 = next small patch
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

## Data and secrets rule

Do not commit:

```text
real API keys
Wi-Fi passwords
private IP credentials
large datasets
trained model binaries
recorded videos with identifiable people unless explicitly approved
```

Use `.gitkeep`, sample JSON, and documentation placeholders instead.

## GUI development rule

Preserve fast preview/development behavior:

```text
Vite hot reload for frontend
FastAPI reload for backend
fake/mock data mode for GUI work
fixed sample detection JSON for visual testing
```

Do not require real camera hardware or a real model just to load the GUI.

## Detection data rule

Detection boxes should be stored in original image coordinates, not displayed-screen coordinates. GUI overlays should convert original image coordinates to display coordinates.

Prefer shared schema files in `packages/schema/` over hard-coded ad-hoc formats.

## Human readability rule

Documentation must be clear enough for a student or teacher to follow. Avoid unexplained jargon. When technical terms are needed, define them briefly.
