# Architecture

## Physical ESP camera path

```text
ESP32-CAM / OV2640 A                    ESP32-CAM / OV2640 B ...
  FB1 + CAMERA_GRAB_LATEST                FB1 + CAMERA_GRAB_LATEST
  PSRAM JPEG framebuffer                  PSRAM JPEG framebuffer
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
                          ├── traffic state / analytics
                          └── Junction Network observation source
```

HTTP port 80 is used for ESP status/config/start/stop control. After Start Stream, each ESP-to-PC image path is one persistent length-prefixed TCP JPEG stream on port 81. Browser clients do not connect directly to the ESP image socket; PC Studio relays the selected shared frame as MJPEG.

The production V0310 tuning keeps one framebuffer. On the normal PSRAM path it uses `CAMERA_GRAB_LATEST` and preserves the existing `ATL1` wire format while replacing the inherited vectored hot-path write with bounded plain `send()` progress capped at 11,680 application bytes per outer write. TCP/lwIP remains responsible for actual packet segmentation. Saved Camera Sources frame size, JPEG quality and target FPS remain authoritative.

Multiple saved ESP sessions may stream concurrently. Each session has an independent worker and newest-frame cache, but exactly one saved ESP is selected to feed the existing shared inference/capture/traffic pipeline. Switching source clears the previous physical frame first and promotes a cached frame only when it is recent; an old cache is never re-stamped as a fresh AI input. Replacing a saved IP retires the previous session generation, so a late frame from that worker is ignored even if the source ID is reused.

If an ESP stream drops or the device reboots, its session can recover using the retained configuration. Simulation temporarily suspends physical image transfer while retaining saved profiles/session intent, and physical streams resume afterward.

## Junction Network observability path

V0311 adds a configuration/observability layer over the existing source and topology services:

```text
config/intersections.json
  junction identity
  node position
  directed links
  source_ids[]
  primary_source_id
          │
          ▼
IntersectionNetworkService
          │
          ├── source → junction resolution
          ├── topology context
          └── persisted layout / camera assignment
                          │
RemoteCameraManager ──────┤ camera health / selected source
CameraFrameService ───────┤ current shared frame source
traffic state ────────────┤ current vehicle/pedestrian/decision data
                          ▼
             JunctionNetworkOverviewService
                          │
                          ▼
           GET /api/traffic/network/overview
                          │
                          ▼
               JunctionNetworkPage
               nodes / lines / load
               cameras / events / warnings
```

One junction may own several camera/source IDs. A source ID remains exclusive to one junction so source-to-junction identity is unambiguous. The overview service is observational: it does not start cameras, run inference, arbitrate signals, or create extra controller instances.

Only the junction resolved from the **currently shared selected camera/simulation source** receives current live traffic/decision values. Other configured junctions show topology and camera health but explicit unavailable traffic observations. This prevents a multi-camera registry or visual network from being misrepresented as simultaneous multi-junction AI fusion.

## Safety and capability boundary

The multi-camera input architecture and Junction Network page are foundations for later live multi-intersection work. They do **not** currently provide:

- simultaneous independent inference/controller pipelines for all junctions;
- cross-camera object identity or physical transfer matching;
- live emergency-vehicle recognition/priority;
- active public-road signal control.

Network cooperation, pedestrian-aware, vehicle-class and emergency-priority behavior retain their documented simulation/evidence scope unless a later explicit live implementation changes that boundary.
