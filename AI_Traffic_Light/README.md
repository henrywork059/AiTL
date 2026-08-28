# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light simulation prototype.

V035 / `0_3_5` is the current unaccepted candidate. V034 / `0_3_4` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## V035 physical camera

V035 keeps one on-demand ESP MJPEG stream, then hardens it with:
- TCP keepalive/TCP_NODELAY;
- exact multipart Content-Length parsing;
- larger stream reads;
- event-driven browser preview delivery;
- newest-frame backlog dropping;
- automatic session restoration after ESP reboot/loss;
- exponential reconnect backoff and richer transport telemetry.

Connect still transfers zero image bytes. Camera settings remain PC-owned and are applied before Start Stream.

Physical/public-road traffic-signal control remains outside scope.
