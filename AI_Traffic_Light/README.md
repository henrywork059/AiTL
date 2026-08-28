# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light simulation prototype.

## Current candidate

V034 / `0_3_4` is the current unaccepted candidate. V033 / `0_3_3` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## V034 camera transport

V034 keeps the V033 session model but replaces repeated `/capture` requests with one persistent MJPEG stream:

```text
ESP boot → idle
PC Connect → /status only → zero images
PC Start Stream
  → /config (camera settings + target FPS)
  → /start
  → one persistent :81/stream connection
  → CameraFrameService
  → Live AI / Dataset / Zones / Analytics
PC Stop Stream
  → close stream
  → /stop
```

Camera Sources preview now uses a backend MJPEG relay from the same current-frame pipeline, removing the old UI dependence on status-poll-driven still-image refresh.

Recommended first physical settings are VGA, JPEG quality 12–16, and 15 FPS. Stable Wi-Fi may support 20 FPS; lower resolution or higher JPEG-quality number reduces bandwidth.

All existing simulation, inference/training, zones, analytics, signal scenarios, network experiments and evidence remain prototype functions. Physical/public-road traffic control remains outside scope.
