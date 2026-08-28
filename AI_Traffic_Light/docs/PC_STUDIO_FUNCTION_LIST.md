# PC Studio Function List — V036 camera highlights

## Camera

- private-LAN ESP status/control connection with Connect transferring zero image bytes;
- PC-owned OV2640 settings and target FPS;
- persistent length-prefixed binary TCP JPEG transport from each ESP on port 81;
- TCP keepalive / `TCP_NODELAY` / bounded stream timeout and reconnect handling;
- fixed 16-byte `ATL1` header carrying JPEG length, sequence and ESP uptime;
- exact fixed-length frame reads with JPEG validation;
- automatic ESP session recovery after reboot/loss;
- exponential reconnect backoff plus FPS/reconnect/recovery/sequence-gap telemetry;
- up to 12 persisted ESP camera profiles with IP/FPS/OV2640 settings;
- independent background TCP workers and newest-frame cache per connected ESP;
- one explicitly selected ESP feeds the shared Live AI / Dataset Capture / zones / analytics pipeline;
- freshness-guarded switching so stale caches, retired sessions and old-IP frames cannot replace the selected source;
- simulation pause/resume across physical ESP streams;
- backend shutdown disconnects all active ESP sessions;
- legacy raw JPEG/PNG upload compatibility;
- browser preview remains the backend MJPEG relay rather than opening additional browser→ESP streams.

Existing inference, dataset/training, zones, tracking/analytics, signal simulation, network experiments and decision evidence remain available.

Multiple ESP image streams do **not** imply multiple simultaneous independent live signal controllers, ESP-side inference, or physical/public-road traffic-signal authority.
