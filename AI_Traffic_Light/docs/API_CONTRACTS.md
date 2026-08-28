# API Contracts — V035 camera transport highlights

Existing non-camera contracts remain unchanged.

## Connect

`POST /api/camera/remote/connect`

Connect probes ESP `/status` only and transfers zero image bytes.

## Start

`POST /api/camera/remote/start`

Body continues to contain:
- `target_fps` 1–30;
- the complete V033/V034 OV2640 settings object;
- legacy `fetch_interval_ms` remains accepted as a compatibility alias.

Ordering remains:

```text
/stop best effort
/config?<settings + stream_fps>
/start
persistent :81/stream
```

## Persistent transport

The backend now parses the ESP multipart response by boundary + `Content-Length`, not JPEG marker scanning. It keeps the newest complete frame when more than one is already buffered.

On transport failure, V035 probes `/status`. If `session_active=false`, it automatically reapplies the retained configuration and calls `/start` before reconnecting.

## Preview

`GET /api/camera/live.mjpeg`

For physical ESP frames, the relay is event-driven: the ingestion thread notifies the relay when a new frame is stored. Simulation and legacy upload retain bounded polling fallback behavior.

Response disables caching/transformation/buffering where supported.

## Status additions

- `stream_connected`
- `session_recoveries`
- `consecutive_failures`
- `reconnect_backoff_ms`
- `last_stream_connected_at_ms`
- `last_recovery_at_ms`

Private RFC1918 IPv4 restriction remains. No redirects or public-road signal-control API are introduced.
