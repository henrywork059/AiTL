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
