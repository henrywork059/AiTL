# PC Studio Frontend — V024 candidate

React/Vite GUI for the AI Traffic Light PC Studio prototype.

Visual styling is governed by `docs/PC_STUDIO_DESIGN_SYSTEM.md` and role tokens under `src/styles/`. V024 uses a Material-inspired role hierarchy rather than a generic dashboard palette: neutral surfaces dominate, primary blue identifies navigation/main actions, secondary teal is selective for progress/selection, and success/warning/error colors are semantic only.


## V024 polling hardening

`src/lib/useSerialPolling.ts` is the shared scheduler for top-level periodic API refreshes. Camera status and Live AI traffic/zone context now schedule the next refresh only after the previous async request settles, preventing overlapping interval requests during a slow backend response. The existing live-detection loop remains self-serial.

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

The visual system follows the operating-system appearance. Dark mode retains the Material 2 `#121212` base with progressively lighter elevated surfaces. Primary/secondary controls have explicit readable on-colors, generic badges are neutral, and traffic-signal colors remain separate from application state. Decorative gradient/glass/neon AI styling is intentionally excluded.

Visible interface copy follows the same design discipline: describe the current task/state, use concise action verbs, make destructive effects explicit, avoid stale release-history language on normal working pages, and state the simulation-only boundary precisely.

Run:

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

The frontend is a supervised prototype UI and is not connected to physical public-road traffic infrastructure.
