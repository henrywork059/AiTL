# PC Studio Frontend — V020 candidate

React/Vite GUI for the AI Traffic Light PC Studio prototype.

## Current working surfaces

- Dashboard with current project/version and live smoke-test state;
- Live AI receiver/simulation preview with trained-model boxes, saved zone overlays, visibility controls, and a compact simulated traffic signal;
- Camera receiver plus density/pause-controlled simulation;
- persistent polygon Zone Editor drawn directly over the current camera/simulation frame;
- live zone-count and simulation-only Traffic Logic view;
- dataset capture, capture deletion, manual review/labeling, and managed YOLO dataset build;
- local training controls with a live convergence plot and early-stop patience;
- Model Registry for load/default/delete actions;
- persistent runtime Settings;
- recent real backend Logs & Errors.

When the backend is unavailable, limited local fixture data may still render so the frontend can show an offline state. Working connected pages use the real backend APIs rather than the legacy mock fixtures.

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
