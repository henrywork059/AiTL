# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light simulation prototype.

V037 / `0_3_7` is the current unaccepted candidate. V036 / `0_3_6` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## V037 physical camera

V037 retains V036 HTTP control plus the persistent TCP image path on port 81 and adds adaptive ESP-side JPEG pressure control to shrink payloads when send time cannot sustain the configured load.

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

### V037 adaptive transport
Physical V036 R6 logs showed that TCP could stay connected but 11–22 KB JPEGs still consumed 100–500+ ms to send. V037 keeps the R6 non-blocking vectored sender and dynamically increases JPEG compression when send pressure is high, then slowly returns toward the saved quality when the link is healthy. New profiles default to QVGA / JPEG 24 / 15 FPS. Reflash V037 firmware to use this behavior.
