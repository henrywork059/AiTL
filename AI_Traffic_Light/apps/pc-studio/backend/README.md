# PC Studio Backend

V035 RemoteCameraService owns:
- status/control-only Connect;
- PC-owned camera configuration;
- persistent MJPEG transport;
- PC TCP keepalive/socket timeout;
- multipart Content-Length parsing;
- newest-frame dropping;
- event notification for browser preview;
- reconnect backoff;
- automatic ESP session recovery after reset/loss.

CameraFrameService remains the downstream common latest-frame surface.
