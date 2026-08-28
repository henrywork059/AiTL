# Code Structure Rules

AiTL keeps one clear owner for each behavior. Routes translate HTTP; services own behavior; pages coordinate UI behavior; reusable mechanics stay in components/helpers.

## Backend

```text
apps/pc-studio/backend/app/
  main.py
  models.py
  core/
  routes/
  services/
```

Relevant camera ownership:

- `services/camera_frames.py` — canonical latest-frame and built-in simulation state;
- `services/remote_camera.py` — V032 private-LAN CameraWebServer probe/pull worker and remote health only;
- `routes/camera.py` — thin camera HTTP surface;
- `main.py` — stops the remote worker during application shutdown.

Do not put inference or traffic policy into the remote transport service.

Other established ownership remains unchanged: `signal_rules.py` owns protected simulated timing; experiment services own isolated benchmarks; `intersection_network.py` owns topology; decision context/evidence services are non-controlling projections.

## Frontend

```text
src/App.tsx
src/pages/
src/components/
src/api.ts
src/lib/apiClient.ts
src/lib/remoteCameraApi.ts
src/lib/useSerialPolling.ts
src/types.ts / types/
src/constants/
src/styles/
```

Camera Sources page owns camera-source UI state. `remoteCameraApi.ts` owns V032 remote-camera API calls/types. Async polling uses the serial scheduler.

## Data / safety rules

Runtime data is not patch content. Canonical image/zone coordinates remain unchanged. Remote ESP frames enter the same CameraFrameService path as other real device frames.

Remote camera integration is an input adapter, not a public-road controller and not a second signal-policy architecture.
