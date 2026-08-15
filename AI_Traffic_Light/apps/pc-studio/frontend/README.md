# PC Studio Frontend — V022 candidate

React/Vite GUI for the AI Traffic Light PC Studio prototype.

## Current working surfaces

- Dashboard with current project/version and live smoke-test state;
- Live AI receiver/simulation preview with trained-model boxes, stable prototype track IDs, saved zone/line overlays, visibility controls, and a compact signal synchronized to the simulation agents;
- Camera receiver plus density/pause-controlled signal-aware simulation with lane/stop-line vehicle behavior and curb/WALK pedestrian behavior;
- persistent camera-aligned Zone Editor supporting polygon regions plus two-point counting lines;
- live zone-count and simulation-only Traffic Logic view;
- analytics-only counting regions created in the existing Zone Editor;
- Traffic Analytics with separate Occupancy and Flow / Tracks modes, unique directional passage plots, region entry/exit/dwell summaries, event table, CSV export, and separate clear actions;
- dataset capture, capture deletion, manual review/labeling, and managed YOLO dataset build;
- local training controls with a live convergence plot and early-stop patience;
- Model Registry for load/default/delete actions;
- persistent runtime Settings;
- recent real backend Logs & Errors.

Occupancy remains sampled per-frame data. Flow mode uses cross-frame track IDs and counts a unique passage only when a track crosses a configured counting line; region entry/exit/dwell are recorded separately. The tracker is intentionally lightweight and can lose/swap IDs under heavy occlusion. When the backend is unavailable, limited local fixture data may still render so the frontend can show an offline state. Working connected pages use the real backend APIs rather than the legacy mock fixtures.

## Release metadata

Frontend fallback/navigation version labels use the shared `src/constants/projectVersion.ts` constant rather than repeating the current release string in each page/API fixture. `scripts/check_structure.py` verifies that this shared frontend value matches root `AI_Traffic_Light/VERSION` and that known version surfaces use the shared constant.

Root `VERSION` remains the authoritative project release state; the frontend constant is a build-safe mirror checked during repository validation.

## Run

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

Open `http://localhost:5173/`.

The frontend is a supervised prototype UI and is not connected to physical public-road traffic infrastructure.
