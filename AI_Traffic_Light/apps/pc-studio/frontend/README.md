# PC Studio Frontend — V017 candidate

React/Vite GUI for the AI Traffic Light PC Studio prototype.

## Current working surfaces

- Dashboard with current project/version and live smoke-test state;
- Live AI receiver/simulation preview with trained-model overlays and visibility controls;
- Camera receiver plus density/pause-controlled simulation;
- persistent polygon Zone Editor;
- live zone-count and simulation-only Traffic Logic view;
- dataset capture, manual review/labeling, and managed YOLO dataset build;
- local training controls with a live convergence plot and early-stop patience;
- Model Registry for load/default/delete actions;
- persistent runtime Settings;
- recent real backend Logs & Errors.

When the backend is unavailable, limited local fixture data may still render so the frontend can show an offline state. Working connected pages use the real backend APIs rather than the legacy mock fixtures.

## Run

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

Open `http://localhost:5173/`.

The frontend is a supervised prototype UI and is not connected to physical public-road traffic infrastructure.
