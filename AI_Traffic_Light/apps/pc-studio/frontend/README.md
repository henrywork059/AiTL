# PC Studio Frontend

React/Vite GUI for the AI Traffic Light PC Studio App.

## Current state — 0_1_0

This frontend is **test-ready with mock data**.

It can:

```text
- start locally with Vite
- connect to the FastAPI backend mock endpoints
- fall back to local mock data if the backend is offline
- display the mock Live AI view
- show mock detections, zones, logs, and traffic state
```

It cannot yet:

```text
- open a real webcam
- read ESP-CAM stream
- run YOLO inference
- save dataset captures
- train/export models
```

## Run

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Optional build check

```bash
npm run typecheck
npm run build
```
