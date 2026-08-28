# Start Here — V034

V034 / `0_3_4` is the current unaccepted candidate. V033 is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Why V034

V033 used a new HTTP `/capture` request for every frame. That is simple but adds connection/request overhead and limits practical frame rate.

V034 uses one persistent ESP MJPEG connection after Start Stream:

```text
Connect: GET /status only
Start:
  POST /config + target_fps
  POST /start
  GET :81/stream   ← stays open
Stop:
  close stream
  POST /stop
```

The backend extracts JPEGs continuously and stores each newest frame in the existing CameraFrameService.

Camera Sources displays `/api/camera/live.mjpeg`, so preview refresh is no longer coupled to the frontend status-poll interval.

Use the matching V034 Arduino firmware. Start with VGA / JPEG quality 12–16 / 15 FPS.

V034 also drops older complete JPEGs if more than one frame arrives in the same network read, preferring the newest frame to avoid backlog latency.
