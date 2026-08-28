# PC Studio Frontend

React/Vite GUI for the AiTL local prototype. Root `AI_Traffic_Light/VERSION` defines release state.

## Working surfaces

PC Studio includes Dashboard, Camera Sources, Live AI, Zone Editor, Traffic Logic, Simulation Lab, Traffic Analytics, Dataset Capture/Review, Train/Export, Model Registry, Settings and Logs.

## V032 Camera Sources

Camera Sources now supports three prototype input paths:

1. **ESP32-CAM by IP** — enter the private LAN IP of a stock Arduino CameraWebServer device;
2. **legacy device upload** — JPEG/PNG posted to the backend receiver;
3. **built-in simulation**.

For the ESP path, the page calls the PC backend remote-camera API. When healthy, it uses the ESP `:81/stream` URL for the preview and falls back to the backend latest-frame image if the direct MJPEG cannot render. The backend independently pulls `/capture` snapshots so Live AI, Dataset Capture and the rest of the PC-side pipeline receive normal CameraFrameService frames.

Starting simulation temporarily replaces the displayed/processed source and pauses ESP snapshot ingestion. Stopping simulation resumes the configured ESP source.

## Frontend ownership

```text
src/App.tsx          top-level composition/navigation
src/pages/           page behavior/state
src/components/      reusable presentation
src/api.ts           existing typed domain API functions
src/lib/apiClient.ts shared envelope/error handling
src/lib/remoteCameraApi.ts V032 remote-camera API helper/types
src/lib/useSerialPolling.ts non-overlapping periodic refresh
src/types.ts/types/  shared contracts
src/constants/       navigation/release metadata
src/styles/          shared design system
```

The Camera Sources remote status loop uses serial polling so requests do not overlap.

## Local frontend run

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

## Safety boundary

Camera streams, signal graphics, decisions and experiments remain prototype/simulation UI. The frontend does not command physical/public-road traffic infrastructure.
