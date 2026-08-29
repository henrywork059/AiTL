# PC Studio Function List — camera and diagnostics highlights

## Camera

- private-LAN ESP status/control connection with Connect transferring zero image bytes;
- PC-owned OV2640 settings and target FPS;
- persistent length-prefixed binary TCP JPEG transport from each ESP on port 81;
- TCP keepalive / `TCP_NODELAY` / bounded stream timeout and reconnect handling;
- fixed 16-byte `ATL1` header carrying JPEG length, sequence and ESP uptime;
- exact fixed-length frame reads with JPEG validation;
- quality-preserving R6 camera behavior: configured JPEG quality/resolution stay fixed across transport pressure;
- automatic ESP session recovery after reboot/loss;
- serialized/retried low-rate ESP HTTP control requests from the R7 PC control path;
- exponential reconnect backoff plus FPS/reconnect/recovery/sequence-gap telemetry;
- up to 12 persisted ESP camera profiles with IP/FPS/OV2640 settings;
- independent background TCP workers and newest-frame cache per connected ESP;
- one explicitly selected ESP feeds the shared Live AI / Dataset Capture / zones / analytics pipeline;
- freshness-guarded switching so stale caches, retired sessions and old-IP frames cannot replace the selected source;
- simulation pause/resume across physical ESP streams;
- backend shutdown disconnects all active ESP sessions;
- legacy raw JPEG/PNG upload compatibility;
- browser preview remains the backend MJPEG relay rather than opening additional browser→ESP streams.

## Camera Diagnostics

The Camera Test page provides a one-button diagnostic for the selected saved ESP. One run measures:

- direct `/status` control reachability and latency;
- AiTL camera/stream protocol compatibility and `camera_ready`;
- RSSI, BSSID and Wi-Fi channel telemetry;
- direct `ATL1`/JPEG receiving that bypasses the normal PC Studio stream worker;
- direct camera receiving while `/status` polling runs concurrently;
- the normal `RemoteCameraManager` / `RemoteCameraService` managed stream path;
- ESP send-failure/deadline telemetry before/after the direct phases;
- restoration of the previous camera settings/FPS and connected/streaming/simulation state.

The result classifies the most likely failing layer, including control unreachable, incompatible firmware, camera-not-ready, ESP camera/TCP send stall, direct-stream failure, control/stream contention, PC Studio stream integration, intermittent control-plane response, weak Wi-Fi margin, or healthy-now.

Existing inference, dataset/training, zones, tracking/analytics, signal simulation, network experiments and decision evidence remain available.

Multiple ESP image streams and camera diagnostic results do **not** imply multiple simultaneous independent live signal controllers, ESP-side inference, validated production reliability, or physical/public-road traffic-signal authority.
- one-click detailed camera diagnostics covering functionality, stability scoring, throughput/jitter, reconnect, and bottleneck attribution;
