# PC Studio Backend

`RemoteCameraService` owns the local physical-camera transport lifecycle:
- status/control-only Connect;
- PC-owned camera configuration;
- persistent length-prefixed TCP JPEG transport from ESP port 81;
- PC TCP keepalive, `TCP_NODELAY`, read timeout and reconnect lifecycle;
- exact fixed-header/frame reads with JPEG validation;
- event notification for the browser preview relay;
- bounded exponential reconnect backoff;
- automatic ESP session recovery after reset/loss.

`CameraFrameService` remains the common downstream latest-frame surface used by preview, inference, dataset capture, zones and analytics. `GET /api/camera/live.mjpeg` remains browser-facing MJPEG; the ESP→PC image hop is not MJPEG in V036.
