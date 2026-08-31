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

### Camera ownership

- `services/camera_frames.py` — canonical selected physical frame plus built-in simulation state;
- `services/remote_camera.py` — one ESP32-CAM HTTP-control + persistent TCP-JPEG transport session, protocol validation, recovery and telemetry;
- `services/remote_camera_manager.py` — persistent saved-camera profiles, one session per ESP, per-camera newest-frame caches and selected-source arbitration into the shared frame service;
- `routes/camera.py` — thin camera HTTP surface;
- `main.py` — shuts down every remote-camera session during backend shutdown.

Production camera transport tuning belongs in the device-camera firmware/transport implementation, not in inference or traffic services. Multi-camera selection is an input-routing function, not a second traffic controller.

### Junction/network ownership

- `services/intersection_network.py` — persisted junction identity, directed topology links, source-to-junction mapping, optional primary source and logical node position;
- `services/junction_network_overview.py` — read-only projection of topology + saved ESP health + the current shared-source traffic/decision observation for the Junction Network UI;
- `services/decision_context.py` — non-controlling explanation projection for one resolved live/simulation observation;
- `routes/traffic.py` — thin `/network`, `/network/context`, `/network/overview` HTTP surfaces.

Do not move camera connection state into `intersection_network.py`. Do not move source/topology persistence into `junction_network_overview.py`. The overview service must not start/stop cameras, run inference, mutate signal timing, or fabricate live values for unobserved junctions.

One junction may own several source IDs. A source ID remains exclusive to one junction. The shared `CameraFrameService` still exposes one selected active source, so camera assignment does not imply simultaneous multi-junction inference.

Other established ownership remains unchanged: `signal_rules.py` owns protected simulated timing; experiment services own isolated benchmarks; `network_policy_arbiter.py` owns pure experiment overlay selection; decision evidence remains a non-controlling stored projection.

## Frontend

```text
src/App.tsx
src/pages/
src/components/
src/api.ts
src/lib/apiClient.ts
src/lib/remoteCameraApi.ts
src/lib/junctionNetworkApi.ts
src/lib/useSerialPolling.ts
src/types.ts / types/
src/constants/
src/styles/
```

- Camera Sources owns saved-ESP selection/editing state.
- `remoteCameraApi.ts` owns typed saved-profile, select/connect/start/stop/disconnect calls.
- `JunctionNetworkPage.tsx` owns the editable node/link workspace and camera-assignment interactions.
- `junctionNetworkApi.ts` owns the typed network overview/save/reset HTTP calls.
- `types/junctionNetwork.ts` owns the frontend Junction Network contract shapes.
- `App.tsx` only wires the page into navigation/composition; it must not absorb junction business logic.
- Async polling uses the shared serial scheduler so periodic requests cannot overlap.

## Regression ownership

Every new automatic regression should be runnable with **no command-line arguments** and use the `scripts/test_*.py` naming convention so `scripts/update_test_run.ps1` discovers it automatically. Hardware/interactive utilities that require `--host`, manual input or special firmware must not be introduced as an ordinary zero-argument `test_*.py` regression unless the runner explicitly excludes/documents them.

Focused Junction Network coverage lives in:

- `scripts/test_intersection_network.py` — persistence/validation/source resolution/topology compatibility;
- `scripts/test_junction_network_overview.py` — multi-camera assignment, camera health, observation honesty and route wiring;
- `scripts/test_junction_network_frontend_structure.py` — frontend navigation/API/page wiring guard.

## Data / safety rules

`config/remote_cameras.json` and `config/intersections.json` are ignored runtime/user configuration and are not patch content. Camera registry data stores saved source IDs, private-LAN IPv4 addresses, target FPS, OV2640 settings and last-selected source. Intersection-network data stores junction/source mapping, layout and topology. Live sockets, JPEG bytes and live occupancy are not persisted into those configuration files.

Canonical image/zone coordinates remain unchanged. Junction `position` is presentation-only logical canvas metadata and must not be interpreted as GPS/geospatial truth.

Only the selected ESP/simulation source is published into `CameraFrameService`, so inactive camera streams cannot overwrite Live AI, Dataset Capture, zones/tracking, analytics or the live observation shown for another junction.

Remote camera integration and Junction Network visualization are prototype input/observability layers, not public-road control and not proof of simultaneous independent multi-intersection perception/control.
