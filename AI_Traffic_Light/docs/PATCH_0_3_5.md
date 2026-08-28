# Patch 0_3_5 — Resilient low-latency ESP streaming

## Release state

- Candidate: V035 / `0_3_5`
- Previous candidate: V034 / `0_3_4`
- Passed baseline: V024 / `0_2_4`

## Review findings from V034

V034's persistent MJPEG design is the correct base architecture, but four avoidable latency/stability costs remained:

1. the PC opened the stream through `urllib`, which gave limited control over TCP keepalive/socket behavior;
2. JPEG extraction scanned for SOI/EOI rather than using the multipart `Content-Length` already sent by the ESP;
3. Camera Sources still polled the PC frame slot every 10 ms for preview delivery;
4. after an ESP reboot/session loss, the PC reopened `:81/stream` but did not automatically restore `/config` + `/start`.

## V035 workflow

```text
ESP boot → idle
PC Connect
  → GET /status
  → zero image bytes

PC Start Stream
  → POST /stop best effort
  → POST /config (all OV2640 settings + target FPS)
  → POST /start
  → open one TCP-kept-alive :81/stream
  → parse exact multipart Content-Length frames
  → keep newest complete frame only
  → CameraFrameService
      ├─ event-driven /api/camera/live.mjpeg
      ├─ Live AI
      ├─ Dataset Capture
      ├─ Zones
      └─ analytics

If stream fails:
  → close socket
  → GET /status
  → if ESP session was lost: /config → /start
  → bounded exponential backoff
  → reopen :81/stream

Stop:
  → close active stream immediately
  → POST /stop
  → idle
```

## Connection stability

PC stream socket:
- TCP_NODELAY;
- SO_KEEPALIVE;
- platform-supported TCP keepalive idle/interval/count;
- 2.5 s stream read timeout.

ESP stream server:
- TCP_NODELAY via HTTP server open callback;
- keepalive idle 3 s / interval 1 s / count 3;
- send/receive wait timeout 2 s;
- Wi-Fi power saving remains disabled;
- Wi-Fi reconnect uses `WiFi.reconnect()` before falling back to `WiFi.begin()`.

## Performance

- stream read block: 64 KiB instead of 4 KiB;
- exact Content-Length parser;
- no physical-frame preview polling delay;
- two HTTPD chunk writes per frame (multipart header + JPEG) instead of three;
- `CAMERA_GRAB_LATEST` + two PSRAM framebuffers retained;
- backlog frames are intentionally discarded rather than replayed.

## Telemetry

Remote status adds:
- `stream_connected`;
- `session_recoveries`;
- `consecutive_failures`;
- `reconnect_backoff_ms`;
- `last_stream_connected_at_ms`;
- `last_recovery_at_ms`.

No public-road signal authority is added.


## Same-candidate physical-stream repair

Physical testing showed:

```text
cam_hal: FB-OVF
stream_client=connected
stream_frame_count=0
measured_fps≈0.3
frame_age≈2 s
```

The root cause is in the camera-buffer allocation profile, not the V035 PC session workflow.

The first V035 ESP file initialized `esp_camera` at VGA and later allowed PC Studio to
raise the sensor frame size at runtime. Espressif's CameraWebServer instead initializes
JPEG mode at UXGA before dropping the sensor to a lower operating resolution so PSRAM
frame buffers are preallocated for the maximum supported image size.

This same-candidate repair therefore:

- initializes the PSRAM JPEG camera profile at UXGA / quality 10 / two frame buffers /
  `CAMERA_GRAB_LATEST`, then applies the PC-selected runtime resolution;
- retains VGA as the default runtime setting;
- keeps two PSRAM buffers and newest-frame capture;
- raises the ESP stream send/receive wait timeout from 2 s to 5 s;
- raises the PC stream read timeout from 2.5 s to 6 s so a temporary camera stall does
  not immediately trigger a reconnect loop;
- adds ESP frame-byte/frame-time/send-time/actual-FPS telemetry.

No V036 version bump is made. This is a repair of the still-unaccepted V035 candidate.
