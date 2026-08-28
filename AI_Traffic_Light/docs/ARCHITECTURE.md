# Architecture — V035 camera path

```text
ESP32-CAM / OV2640
  CAMERA_GRAB_LATEST
  2 PSRAM framebuffers
  Wi-Fi sleep disabled
  HTTPD keepalive + TCP_NODELAY
       │
       │ one persistent MJPEG connection
       ▼
RemoteCameraService
  direct HTTPConnection
  TCP keepalive
  Content-Length multipart parser
  newest-frame policy
  reconnect + session recovery
       │
       ▼
CameraFrameService
       ├── Condition wakeup → /api/camera/live.mjpeg
       ├── Live AI
       ├── Dataset
       ├── Zones
       └── analytics
```

There is still one physical ESP→backend image stream. The browser does not open a second ESP stream.

If the ESP reboots, the backend can restore the retained session configuration automatically rather than requiring a manual Stop/Start cycle.

Simulation suspends the physical image stream while retaining the configured remote camera state.
