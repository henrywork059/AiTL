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

- `services/camera_frames.py` — canonical selected physical frame plus built-in simulation state;
- `services/remote_camera.py` — one ESP32-CAM HTTP-control + persistent TCP-JPEG transport session, protocol validation, recovery and telemetry;
- `services/remote_camera_manager.py` — persistent saved-camera profiles, one session per ESP, per-camera newest-frame caches and selected-source arbitration into the shared frame service;
- `routes/camera.py` — thin camera HTTP surface;
- `main.py` — shuts down every remote-camera session during backend shutdown.

Do not put inference or traffic policy into the transport/manager services. Multi-camera selection is an input-routing function, not a second traffic controller.

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

Camera Sources owns saved-ESP selection/editing state. `remoteCameraApi.ts` owns the typed saved-profile, select/connect/start/stop/disconnect API calls. Async polling uses the serial scheduler.

## Data / safety rules

`config/remote_cameras.json` is ignored runtime/user configuration and is not patch content. It stores saved source IDs, private-LAN IPv4 addresses, target FPS, OV2640 settings and the last-selected source; live socket state and JPEG bytes are not persisted.

Canonical image/zone coordinates remain unchanged. Only the selected ESP is published into `CameraFrameService`, so inactive camera streams cannot overwrite Live AI, Dataset Capture, zones/tracking or analytics.

Remote camera integration is an input adapter, not public-road control and not proof of simultaneous independent multi-intersection perception/control.
