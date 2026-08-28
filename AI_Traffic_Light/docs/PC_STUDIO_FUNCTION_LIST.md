# PC Studio Function List — V035 highlights

## Camera

- private-LAN ESP status/control connection;
- Connect with zero image transfer;
- PC-owned OV2640 settings and target FPS;
- one persistent MJPEG transport;
- TCP keepalive / stream timeout handling;
- exact multipart Content-Length parsing;
- newest-frame backlog dropping;
- event-driven physical-camera browser preview;
- automatic ESP session recovery after reboot/loss;
- exponential reconnect backoff;
- measured FPS, reconnect, recovery and failure telemetry;
- simulation pause/resume;
- legacy raw JPEG/PNG upload compatibility.

Existing inference, dataset/training, zones, tracking/analytics, signal simulation, network experiments and decision evidence remain available.

Independent simultaneous per-camera buffers and physical/public-road signal control remain outside the current implementation.
