# PC Studio Backend

`RemoteCameraService` owns one physical ESP transport lifecycle. `RemoteCameraManager` owns the saved multi-camera registry and active-source selection:
- persistent per-camera IP/source/FPS/OV2640 profiles under runtime `config/remote_cameras.json`;
- independent status/control-only Connect per saved ESP;
- PC-owned camera configuration;
- persistent length-prefixed TCP JPEG transport from ESP port 81;
- PC TCP keepalive, `TCP_NODELAY`, read timeout and reconnect lifecycle;
- exact fixed-header/frame reads with JPEG validation;
- event notification for the browser preview relay;
- bounded exponential reconnect backoff;
- automatic ESP session recovery after reset/loss;
- per-ESP newest-frame caches so several streams may stay active while exactly one selected ESP feeds the shared downstream frame service;
- freshness-guarded source switching so stale caches/old-IP frames cannot masquerade as a new selected frame;
- backend lifespan shutdown that disconnects every active ESP session.

`CameraFrameService` remains the common downstream latest-frame surface used by preview, inference, dataset capture, zones and analytics. `GET /api/camera/live.mjpeg` remains browser-facing MJPEG; the ESP→PC image hop is not MJPEG in V036.
