# PC Studio Frontend

React/Vite GUI for the AI Traffic Light PC Studio App.

## Current state — 0_1_2

This frontend is **test-ready for persistent frame capture with an optional labeled-dataset training panel**.

It can:

```text
- start locally with Vite
- connect to the FastAPI backend mock endpoints
- fall back to local mock data if the backend is offline
- display the mock Live AI view
- show mock detections, zones, logs, and traffic state
- preview and save the current receiver or simulation frame
- show persistent image/metadata counts and saved paths
- configure and monitor an optional background YOLO training run
```

It cannot yet:

```text
- open a real webcam
- read ESP-CAM stream
- run YOLO inference
- label bounding boxes
- train directly from unlabeled captures
- export models
```

## Run

```bash
npm ci
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
