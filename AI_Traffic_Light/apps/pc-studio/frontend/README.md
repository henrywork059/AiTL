# PC Studio Frontend — V023 candidate

React/Vite GUI for the AI Traffic Light PC Studio prototype.

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

Run:

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

The frontend is a supervised prototype UI and is not connected to physical public-road traffic infrastructure.
