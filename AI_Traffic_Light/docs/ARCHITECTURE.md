# Architecture

AiTL is a local/student-scale computer-vision and traffic-light simulation prototype. No layer sends commands to physical/public-road traffic infrastructure.

## 1. Live camera / single-intersection path

```text
stock ESP32 CameraWebServer ── GET /capture ─┐
legacy JPEG/PNG upload ──────────────────────┼→ CameraFrameService
synthetic camera ────────────────────────────┘
                                               ↓
                                      local inference/tracking
                                               ↓
                              zones + occupancy/flow/class observations
                                               ↓
                                    traffic-state evaluation
                                               ↓
                                 ranked simulated signal controller
                                               ↓
                                     PC Studio / capture / analytics
```

V032 adds `RemoteCameraService` only at the transport boundary. It does not own detection, analytics or signal policy.

### Remote ESP transport

```text
ESP32-CAM + OV2640
  stock Arduino CameraWebServer
        │
        ├── GET /capture  ← backend RemoteCameraService
        │                       │
        │                       └→ validated JPEG → CameraFrameService
        │
        └── :81/stream   ← browser Camera Sources preview
```

The backend allows only literal RFC1918 IPv4 camera hosts. Remote configuration is in process memory. Starting built-in camera simulation pauses remote ingestion; stopping simulation resumes it.

## 2. Signal ownership

`signal_rules.py` remains the sole owner of ranked scenario arbitration and protected phase/timing behavior. Camera services supply frames/observations only.

## 3. Isolated single-junction Simulation Lab

```text
saved profile + zones + density + seed
        ↙                     ↘
 Fixed simulator          Adaptive simulator
 + isolated controller    + isolated controller
        ↘                     ↙
       aligned synthetic telemetry
```

This path is separate from live camera/controller state.

## 4. Intersection/network and evidence path

`intersection_network.py` owns generic intersection/source identity and directed topology metadata.

The isolated network benchmark creates separate per-intersection controller runtimes and synthetic transfer/predicted-arrival evidence. The seven current modes are comparison/ablation variants, not one all-features-integrated live controller.

`network_policy_arbiter.py` selects one higher-level overlay owner per intersection/tick:
incident hold > active pedestrian crossing > simulated emergency priority > pedestrian max-wait > configured vehicle-class priority > network cooperation.

`decision_context.py` projects non-controlling live explanation context. `decision_evidence.py` projects/persists normalized network-experiment evidence and never mutates signal timing.

## 5. Backend ownership

```text
apps/pc-studio/backend/app/
  main.py                     app/lifecycle/router wiring
  routes/                     HTTP translation
  services/
    camera_frames.py          common latest-frame + simulation store
    remote_camera.py          V032 stock CameraWebServer pull adapter
    signal_rules.py           protected simulated signal policy
    intersection_network.py   topology/source metadata
    decision_context.py       live explanation projection
    simulation_experiments.py isolated single-junction benchmark
    network_simulation_experiments.py isolated network benchmark
    decision_evidence.py      normalized experiment evidence
  core/                       envelopes/errors/logging/version/persistence
```

## 6. Frontend ownership

Camera Sources owns the IP/connect UI. `remoteCameraApi.ts` owns remote camera HTTP calls/types. Shared serial polling prevents overlapping status requests. Other pages continue consuming the common backend frame/status APIs.

## 7. Data semantics

- real ESP frame = physical camera input transported to PC;
- simulation frame = synthetic local scene;
- occupancy = sampled presence;
- flow = track-derived events;
- zone/class count = per-frame observation;
- network experiment telemetry = isolated synthetic evidence;
- live network link = configured metadata.

A physical camera frame does not automatically prove detector accuracy or physical signal authority.

## 8. Hardware boundary

V032 integrates camera **input** only. ESP-side signal LEDs/control commands are not added. Heavy inference, training, analytics and traffic logic remain PC-side.
