# Architecture — V033 camera boundary

## Physical camera transport

```text
AI Thinker ESP32-CAM / OV2640
            │
            │ boot + Wi-Fi
            ▼
        IDLE control server
            │
PC Connect ─┴─ GET /status
            │        no image bytes
            │
PC Start Stream
  ├─ POST /config (complete runtime sensor settings)
  ├─ POST /start
  └─ repeated GET /capture
            │
            ▼
     RemoteCameraService
            │
            ▼
      CameraFrameService
            │
            ├─ Live AI
            ├─ Dataset Capture
            ├─ Zones
            ├─ Tracking/analytics
            └─ traffic-state prototype pipeline
```

RemoteCameraService owns network/session transport only. Signal policy, inference and analytics remain in their established PC services.

Simulation pauses the `/capture` worker. The ESP session may remain active, but no image bytes are sent because the PC is not issuing image requests. Stopping simulation resumes requests.

## Safety

The V033 hardware path is physical camera input. It is not physical/public-road signal authority.
