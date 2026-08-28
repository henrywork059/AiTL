# Architecture

## Physical ESP camera path

```text
ESP32-CAM / OV2640 A                    ESP32-CAM / OV2640 B ...
  CAMERA_GRAB_LATEST                      CAMERA_GRAB_LATEST
  2 PSRAM framebuffers                    2 PSRAM framebuffers
  Wi-Fi sleep disabled                    Wi-Fi sleep disabled
  HTTP control :80                        HTTP control :80
  binary TCP JPEG :81                     binary TCP JPEG :81
          │                                       │
          ▼                                       ▼
   RemoteCameraService                     RemoteCameraService
   independent worker/socket               independent worker/socket
          └───────────────┬───────────────────────┘
                          ▼
                 RemoteCameraManager
                 saved per-camera profile
                 newest-frame cache/source
                 one selected active source
                          │
                          ▼
                  CameraFrameService
                    shared active frame
                          ├── /api/camera/live.mjpeg browser relay
                          ├── Live AI
                          ├── Dataset Capture
                          ├── Zones / tracking
                          └── analytics
```

HTTP port 80 is used for ESP status/config/start/stop control. After Start Stream, each ESP-to-PC image path is one persistent length-prefixed TCP JPEG stream on port 81. Browser clients do not connect directly to the ESP image socket; PC Studio relays the selected shared frame as MJPEG.

Multiple saved ESP sessions may stream concurrently. Each session has an independent worker and newest-frame cache, but exactly one saved ESP is selected to feed the existing shared inference/capture/traffic pipeline. Switching source clears the previous physical frame first and promotes a cached frame only when it is recent; an old cache is never re-stamped as a fresh AI input. Replacing a saved IP retires the previous session generation, so a late frame from that worker is ignored even if the source ID is reused.

If an ESP stream drops or the device reboots, its session can recover using the retained configuration. Simulation temporarily suspends physical image transfer while retaining saved profiles/session intent, and physical streams resume afterward.

This multi-camera input architecture does not create simultaneous independent inference/controllers for several intersections and does not provide physical/public-road signal authority.
