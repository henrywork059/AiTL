# API Contracts — V034 camera transport

Existing non-camera contracts are unchanged.

## Session control

`POST /api/camera/remote/connect`

```json
{"host":"192.168.68.57","source_id":"esp32_cam_01"}
```

Connect performs ESP `/status` only. Zero image bytes are requested.

`POST /api/camera/remote/start`

```json
{
  "target_fps": 15,
  "settings": {
    "frame_size": "VGA",
    "jpeg_quality": 12
  }
}
```

The complete existing V033 OV2640 settings object is still required. V034 adds `target_fps` 1–30. The backend sends it to ESP `/config` as `stream_fps`.

For compatibility, `fetch_interval_ms` is still accepted; when supplied by an older V033 client it is converted to an equivalent bounded target FPS.

Start ordering:

```text
/stop best effort
/config?<complete settings + stream_fps>
/start
open http://<ESP-IP>:81/stream
```

`POST /api/camera/remote/stop` closes the persistent stream before calling ESP `/stop`.

## Low-latency preview

`GET /api/camera/live.mjpeg`

Returns `multipart/x-mixed-replace; boundary=frame` from the current CameraFrameService frame sequence. This is a PC-side relay, not a second ESP connection.

## Status additions

Remote status includes:

- `transport`: `idle` or `mjpeg`
- `target_fps`
- `measured_fps`
- `last_frame_interval_ms`
- `stream_reconnects`
- `stream_bytes_received`
- `stream_url`

Existing V033 status/session/settings fields remain.

## Safety

Remote targets remain literal RFC1918 IPv4 only and redirects remain disabled. No physical/public-road signal-control API is added.
