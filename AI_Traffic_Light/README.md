# AI Traffic Light — Initial Project Skeleton

Current patch: **0_0_3**  
Baseline skeleton: **0_0_0**

This repository contains the starter structure for an **AI vision-based adaptive traffic light project**.

The project is designed around two main parts:

1. **PC Studio App**
   - Runs on the computer.
   - Receives camera/video frames.
   - Runs object detection and possible future segmentation.
   - Counts pedestrians and vehicles inside traffic zones.
   - Simulates traffic-light decisions.
   - Captures datasets and later trains/exports models.

2. **Device Camera App**
   - Runs on an ESP32-CAM or similar camera node.
   - Captures frames and sends them to the PC.
   - Does **not** train AI and does **not** run heavy AI inference.

The current project state is a **starter skeleton**, not a finished product. It contains placeholder GUIs, mock APIs, schemas, documentation, logging/error-code scaffolding, and folder structure so development can begin cleanly.

## Recommended first milestone

Build this before adding ESP-CAM or custom training:

```text
Video/webcam input
→ pretrained object detection
→ zone-based counting
→ rule-based traffic-light simulation
→ GUI visualization
```

## Repository layout

```text
AI_Traffic_Light/
  apps/
    pc-studio/
      backend/              Python / FastAPI backend placeholder
      frontend/             React / Vite GUI placeholder
    device-camera/
      esp32-cam/            ESP32-CAM firmware placeholder
  packages/
    schema/                 Shared JSON schemas and class definitions
    ui/                     Shared UI component design notes
  config/                   Project-level default config
  docs/                     Instructions and design notes
  samples/                  Sample images/videos/predictions placeholders
  scripts/                  Helper scripts
  AGENTS.md                 Working rules for AI agents
```

## Important documentation

Start with these files:

```text
docs/START_HERE.md                First orientation for the project
docs/HUMAN_GUIDE.md               Human workflow, usage, upload, and safety guide
docs/AI_AGENT_GUIDE.md            Detailed instructions for AI coding/documentation agents
docs/CODE_STRUCTURE.md            Code splitting, module boundaries, and debug rules
docs/API_CONTRACTS.md             Backend/API endpoint and response conventions
docs/ERROR_CODES.md               Error-code ranges and naming rules
docs/DEBUGGING_AND_LOGGING.md     Logging format, request IDs, and debugging workflow
AGENTS.md                         Short root-level rules for AI agents
docs/DEVELOPMENT_WORKFLOW.md      Development flow and milestone order
docs/VERSIONING.md                Version and patch rules
docs/ROADMAP.md                   Project roadmap
```

## Code design rule

All future code should be split into small modules:

```text
app/main.py                 app factory and middleware only
app/routes/                 thin API routes only
app/services/               business logic and AI pipeline calls
app/core/                   logging, error codes, exceptions, API response helpers
frontend/src/components/    small UI components
frontend/src/lib/           API client, logger, frontend utilities
```

Routes should call services. Services should call lower-level utilities. UI components should call shared API helpers, not raw `fetch` scattered across components.

## Development direction

- Use the PC app first with fake/mock data.
- Add webcam/video input next.
- Add YOLO detection after the GUI flow works.
- Add ESP-CAM stream only after the PC prototype is stable.
- Add training after the detection + zone logic is proven.
- Keep documentation, schemas, API contracts, error codes, and app behavior aligned in every patch.

## Version status

```text
0_0_0 = initial skeleton
0_0_1 = documentation/version cleanup
0_0_2 = human and AI-agent instruction docs
0_0_3 = modular code, API contract, logging, and error-code standards
```
