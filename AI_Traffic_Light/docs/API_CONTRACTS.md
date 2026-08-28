# API Contracts — V036 camera transport highlights

Existing non-camera contracts remain unchanged.

## Connect

`POST /api/camera/remote/connect`

Connect probes ESP `/status` only and transfers zero image bytes.

The ESP must report:

```json
{
  "protocol": "aitl-camera-v036",
  "stream_protocol": "aitl-tcp-jpeg-v1",
  "camera_ready": true
}
```

A mismatched older firmware returns the existing camera-not-connected error envelope with HTTP 409 and compatibility details. No new stable error code is introduced.

## Start

`POST /api/camera/remote/start`

Body contains:
- `target_fps` 1–30;
- the complete OV2640 settings object;
- legacy `fetch_interval_ms` remains accepted as a compatibility alias.

Ordering:

```text
/stop best effort
/config?<settings + stream_fps>
/start
persistent TCP connect to ESP :81
```

## Persistent image transport

ESP port 81 is not HTTP in V036. It is one private-LAN TCP stream with repeated frames:

```text
ATL1 | uint32 JPEG length | uint32 sequence | uint32 ESP uptime_ms | JPEG bytes
```

All integer fields are unsigned network byte order. Payload length must be 1..`MAX_FRAME_BYTES`. JPEG SOI/EOI markers are validated before storage.

The backend uses exact header/payload reads. On transport failure it probes `/status`; if `session_active=false`, it reapplies retained configuration and `/start` before reconnecting.

## Browser preview

`GET /api/camera/live.mjpeg`

This HTTP endpoint remains multipart MJPEG. It relays the latest PC-side frame; the browser does not connect to the ESP binary stream directly. Physical frame delivery remains event-driven.

Response disables caching/transformation/buffering where supported.

## Remote status

`GET /api/camera/remote/status`

Existing fields remain, with these V036 semantics/additions:

- `transport`: `idle` or `tcp_jpeg`;
- `stream_protocol`: `null` or `aitl-tcp-jpeg-v1`;
- `stream_url`: `tcp://<private-ip>:81` when configured;
- `source_sequence_gaps`: inferred missing ESP source sequence values;
- `last_remote_sequence`;
- `last_source_uptime_ms`;
- existing connection/recovery/FPS/byte fields remain.

Private RFC1918 IPv4 restriction remains. No redirects or public-road signal-control API are introduced.
