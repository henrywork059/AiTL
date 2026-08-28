# ESP32-CAM V035 streaming

Use the updated standalone `AiTL_ESP32CAM_V035.ino`. `secrets.h` is unchanged.

## Workflow

The ESP boots idle. Connect sends no images.

Start Stream:

```text
/config + stream_fps
/start
persistent :81/stream
```

Stop Stream closes the PC stream and calls `/stop`.

## V035 stability changes

The stream HTTP server enables:
- TCP keepalive;
- TCP_NODELAY;
- 2 s send/receive wait timeout;
- LRU socket purge.

The firmware keeps Wi-Fi sleep disabled and uses `WiFi.reconnect()` before a full `WiFi.begin()` fallback.

`/status` now reports `stream_client_active` so transport state can be diagnosed separately from `session_active`.

## V035 speed changes

Each MJPEG frame uses two HTTPD writes:
1. multipart boundary + headers;
2. JPEG bytes.

V034 used three writes.

The firmware retains:
- `CAMERA_GRAB_LATEST`;
- two PSRAM framebuffers;
- PC-selected 1–30 FPS cap.

Recommended starting point remains VGA, JPEG quality 12–16, 15 FPS. Test 20 FPS only if measured FPS is stable and reconnects stay at zero.
