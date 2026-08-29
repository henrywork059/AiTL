# PC Studio Backend

`RemoteCameraService` owns one physical ESP transport lifecycle. `RemoteCameraManager` owns the saved multi-camera registry and active-source selection:

- persistent per-camera IP/source/FPS/OV2640 profiles under runtime `config/remote_cameras.json`;
- independent status/control-only Connect per saved ESP;
- serialized/retried low-rate HTTP control requests;
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

`CameraFrameService` remains the common downstream latest-frame surface used by preview, inference, dataset capture, zones and analytics. `GET /api/camera/live.mjpeg` remains browser-facing MJPEG; the ESP→PC image hop uses the `aitl-tcp-jpeg-v1` fixed-header JPEG stream.

The current quality-preserving camera firmware preserves saved image quality/resolution under transport pressure. New profile defaults remain QVGA / JPEG 24 / 15 FPS; existing persisted profiles are not replaced by source patches.

## Camera diagnostics

`CameraDiagnosticService` owns the one-click diagnostic workflow exposed through `POST /api/camera/diagnostics/run`. It measures the selected saved ESP through direct control probes, direct ATL1/JPEG receiving, direct receiving with concurrent status polling, and the normal manager/service stream path. It returns measured checks plus an evidence-based likely-failure classification and restores the prior selected-camera/simulation state where possible. The diagnostics service does not own traffic-signal logic or physical/public-road authority.
