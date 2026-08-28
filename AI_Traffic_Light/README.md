# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light simulation prototype.

V036 / `0_3_6` is the current unaccepted candidate. V035 / `0_3_5` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## V036 physical camera

V036 keeps HTTP only for ESP status/config/start/stop control and moves the hot ESP→PC image path to one PC-initiated persistent TCP connection on port 81.

Each frame is JPEG with a fixed 16-byte `ATL1` header carrying payload length, sequence and ESP uptime. The PC reads exact frame lengths, keeps the newest camera frame in the existing `CameraFrameService`, and continues to expose browser-compatible MJPEG from the backend.

Low-latency protections include:
- `CAMERA_GRAB_LATEST` with two PSRAM framebuffers;
- `TCP_NODELAY` and keepalive;
- absolute target-FPS scheduling rather than adding send time to the frame period;
- a bounded ESP send deadline that drops/reconnects instead of accumulating stale TCP backlog;
- event-driven browser preview delivery;
- automatic session restoration after ESP reboot/loss;
- bounded exponential reconnect backoff.

Connect still transfers zero image bytes. Camera settings remain PC-owned and are applied before Start Stream.

Physical/public-road traffic-signal control remains outside scope.
