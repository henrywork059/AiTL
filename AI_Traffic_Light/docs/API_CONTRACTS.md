# API Contracts — V037 camera transport highlights

Existing non-camera contracts remain unchanged.

## Connect

`POST /api/camera/remote/connect`

Connect probes ESP `/status` only and transfers zero image bytes.

The ESP must report:

```json
{
  "protocol": "aitl-camera-v037",
  "stream_protocol": "aitl-tcp-jpeg-v1",
  "camera_ready": true
}
```

V037 PC Studio also accepts `aitl-camera-v036` because V036 uses the same `aitl-tcp-jpeg-v1` wire format. A mismatched older firmware such as V035 returns the existing camera-not-connected error envelope with HTTP 409 and compatibility details. No new stable error code is introduced.

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

ESP port 81 is not HTTP in V037/V036. It is one private-LAN TCP stream with repeated frames:

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

Existing fields remain, with these V037 semantics/additions:

- `transport`: `idle` or `tcp_jpeg`;
- `stream_protocol`: `null` or `aitl-tcp-jpeg-v1`;
- `stream_url`: `tcp://<private-ip>:81` when configured;
- `source_sequence_gaps`: inferred missing ESP source sequence values;
- `last_remote_sequence`;
- `last_source_uptime_ms`;
- existing connection/recovery/FPS/byte fields remain.

Private RFC1918 IPv4 restriction remains. No redirects or public-road signal-control API are introduced.


## Saved multi-camera registry

The saved multi-camera registry retained from V036 provides:

- `POST /api/camera/remote/cameras` — save/update one ESP profile (`host`, `source_id`, `target_fps`, complete settings) and select it;
- `POST /api/camera/remote/select` — select an existing saved ESP without stopping other ESP streams;
- `DELETE /api/camera/remote/cameras/{source_id}` — stop/disconnect that ESP if needed and remove its saved profile.

`GET /api/camera/remote/status` remains backward compatible for the selected camera and additionally returns `active_source_id`, `camera_count`, `cameras`, `multi_camera`, and `max_saved_cameras`. Each `cameras[]` item reports its saved IP/settings plus connected/streaming/reachability state.

Profiles are stored locally in `config/remote_cameras.json` using the existing atomic JSON-store helper. Socket state is never persisted: after PC Studio restarts, the list/settings are restored but devices must be connected again.

Several ESP streams may be active simultaneously. Each has its own TCP worker and newest-frame cache. Only the selected ESP publishes into the existing global `CameraFrameService`; therefore Live AI, Dataset Capture, zones and analytics continue to consume one unambiguous active source. Selecting another already-running ESP promotes its cached newest frame only when it was received recently; otherwise the previous physical frame is cleared and the shared pipeline waits for the next fresh frame from the selected ESP.


## V037 adaptive JPEG telemetry

A V037 device `/status` may additionally report:

- `adaptive_quality_enabled: true`;
- `configured_jpeg_quality`: the PC-saved OV2640 quality floor;
- `effective_jpeg_quality`: the current quality number after adaptive compression;
- `adaptive_quality_adjustments`: number of runtime quality changes;
- `send_ewma_ms`: exponentially weighted send time;
- `adaptive_payload_target_bytes`: current maximum JPEG payload target before local oversize skipping;
- `adaptive_local_frame_drops`: captured oversized JPEGs skipped locally before any ATL1 bytes were written;
- `adaptive_window_learns`: number of times a partial TCP send lowered the conservative payload target;
- `configured_frame_size`: the PC-saved resolution ceiling;
- `effective_frame_size`: the temporary runtime resolution after V037 R4 pressure adaptation;
- `adaptive_resolution_downshifts` / `adaptive_resolution_recoveries`: runtime size-adaptation counters;
- `last_frame_width` / `last_frame_height`: actual dimensions of the most recently captured JPEG.

These fields are diagnostic device telemetry. They do not change the `ATL1` image packet format or PC-side API envelopes.
