# PC Studio Frontend — V023 candidate

React/Vite GUI for the AI Traffic Light PC Studio prototype.

Visual styling is governed by `docs/PC_STUDIO_DESIGN_SYSTEM.md` and the role-token files under `src/styles/`. The interface follows the operating-system light/dark preference, uses neutral layered surfaces with one restrained interaction accent, and reserves red/amber/green for semantic/simulated-signal meaning rather than decorative "AI" styling.

## Current working surfaces

- Dashboard, Live AI, Camera Sources, camera-aligned Zone Editor, Traffic Analytics, Dataset Capture/Review, Train/Export, Model Registry, Settings, and Logs;
- Traffic Logic now contains tabs for **Live Decision**, **Normal Timing**, **Adaptive Rules**, **Safety & Test**, and **Decision History**;
- normal timing editing for all protected simulated signal phases with min/base/max values and cycle/stale/demand-memory limits;
- Fixed / Adaptive / Test modes, named policy profiles, dry-run toggle, Save / Discard / Reset Defaults;
- rule editing for threshold, stable-for duration, adjustment, cooldown, priority, and enable/disable state;
- live active/suppressed/inactive/unavailable rule explanations and effective phase timing;
- manual Test-mode pedestrian/vehicle/mobility/incident inputs, Clear Incident, Reset Adaptive State, and scenario previews;
- runtime signal-decision history display/clear.

Mobility assistance and fall/incident controls are explicit simulation/test inputs. The frontend does not claim the current model can detect wheelchairs or falls.

## Visual system

Shared presentation is isolated under `src/styles/` and documented in `docs/PC_STUDIO_DESIGN_SYSTEM.md`. `src/styles.css` is the stable import entrypoint. Pages may keep small page-specific CSS files for layout/behavior, but they should consume shared design tokens instead of defining independent palettes.

The current visual system is system-adaptive. Light mode uses quiet neutral layers; dark mode follows the Material 2 dark-surface model with a `#121212` base and progressively lighter elevated surfaces. Interaction uses a desaturated Blue Grey family, while semantic/simulated-signal colors remain sparse. Decorative gradient/glass/neon AI styling is intentionally excluded.

Run:

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

The frontend is a supervised prototype UI and is not connected to physical public-road traffic infrastructure.
