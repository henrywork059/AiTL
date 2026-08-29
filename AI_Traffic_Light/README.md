# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light simulation prototype.

V037 / `0_3_7` is the current unaccepted candidate. V036 / `0_3_6` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## V037 physical camera

V037 R6 keeps V036-compatible HTTP control plus persistent `ATL1` TCP JPEG transport, but removes the R2/R4 assumption that a JPEG must fit one ESP lwIP send buffer. Controlled physical testing carried 8 KiB, 16 KiB and 32 KiB framed payloads without TCP failures on a healthy AP, so transport pressure no longer changes image quality or resolution.

Each frame remains JPEG with a fixed 16-byte `ATL1` header carrying payload length, sequence and ESP uptime. PC Studio can save up to 12 ESP profiles, keep several streams active independently, cache the newest frame from each, and select one source for `CameraFrameService`. Browser-compatible MJPEG still comes from the PC backend.

R6 low-latency protections are:
- one PSRAM framebuffer with `CAMERA_GRAB_WHEN_EMPTY` and 20 MHz XCLK;
- `TCP_NODELAY`, keepalive and the existing non-blocking vectored `sendmsg()` path;
- freshness-first target-FPS scheduling with no catch-up backlog;
- 700 ms no-progress / 1500 ms total steady-state send guardrails, with longer per-connection warmup;
- configured JPEG quality and resolution stay fixed if a send slows or fails;
- a partial ATL1 frame closes only that TCP client so PC Studio can reconnect cleanly;
- RSSI, BSSID, channel and ESP Wi-Fi recovery counters are visible in status/Camera Sources.

Connect still transfers zero image bytes. Camera settings remain PC-owned and are applied before Start Stream. Simulation and selected-source isolation remain unchanged. Physical/public-road traffic-signal control remains outside scope.
