# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light simulation prototype.

V036 / `0_3_6` is the current unaccepted candidate. V035 / `0_3_5` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## V036 physical camera

V036 keeps HTTP only for ESP status/config/start/stop control and moves each ESP→PC image path to its own PC-initiated persistent TCP connection on port 81.

Each frame is JPEG with a fixed 16-byte `ATL1` header carrying payload length, sequence and ESP uptime. PC Studio can save up to 12 ESP profiles, retain IP/FPS/OV2640 settings per camera, keep several ESP streams running independently, cache the newest frame from each, and select one active ESP to feed the existing `CameraFrameService`. Browser-compatible MJPEG still comes from the backend.

Low-latency protections include:
- `CAMERA_GRAB_LATEST` with two PSRAM framebuffers;
- `TCP_NODELAY` and keepalive;
- absolute target-FPS scheduling rather than adding send time to the frame period;
- a bounded ESP send deadline that drops/reconnects instead of accumulating stale TCP backlog;
- event-driven browser preview delivery;
- automatic session restoration after ESP reboot/loss;
- bounded exponential reconnect backoff.

Connect still transfers zero image bytes. Camera settings remain PC-owned and are applied before Start Stream. Switching the selected ESP changes the source used by Live AI, Dataset Capture, zones and analytics without forcing other ESP streams to stop. The previous physical frame is cleared during a source change, and only a recent target cache may be promoted.

Physical/public-road traffic-signal control remains outside scope.

### V036 same-candidate hardware repair
The current V036 patch includes a non-blocking ESP TCP send repair (`select()` + `MSG_DONTWAIT`) after hardware logs showed blocking writes causing reconnect storms. Reflash the included V036 ESP firmware when applying the latest full patch.
