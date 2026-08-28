# Architecture — V034 camera path

```text
ESP32-CAM OV2640
  Wi-Fi sleep off
  CAMERA_GRAB_LATEST
  2 PSRAM FBs
       │
       │ persistent :81/stream
       ▼
RemoteCameraService
  incremental JPEG extraction
  reconnect + FPS telemetry
       │
       ▼
CameraFrameService
       ├── /api/camera/live.mjpeg → Camera Sources
       ├── Live AI
       ├── Dataset Capture
       ├── Zones
       └── Analytics / traffic-state inputs
```

V034 avoids a second browser→ESP stream: the PC backend owns the single physical MJPEG transport and relays its latest frames to the UI.

Signal policy, inference, training and analytics ownership are unchanged.

When simulation is active, the backend does not keep consuming the physical ESP stream. This prevents unnecessary image transfer and stale buffering.
