# API Contracts — V033 camera highlights

All JSON PC Studio API responses retain the standard envelope and `meta.request_id`. Existing non-camera APIs remain unchanged.

## Remote ESP status/control

### `POST /api/camera/remote/connect`

Body:

```json
{"host":"192.168.68.57","source_id":"esp32_cam_01"}
```

Validates an RFC1918 literal IPv4 address and probes only ESP `GET /status`. It does **not** request `/capture` and does not start image transfer.

### `GET /api/camera/remote/status`

Returns configured/reachable/worker/streaming/simulation-pause state, ESP identity/status snapshot, current applied settings, fetch counters and last error.

### `POST /api/camera/remote/start`

Body:

```json
{
  "fetch_interval_ms": 250,
  "settings": {
    "frame_size": "VGA",
    "jpeg_quality": 12,
    "brightness": 0,
    "contrast": 0,
    "saturation": 0,
    "special_effect": 0,
    "awb": true,
    "awb_gain": true,
    "wb_mode": 0,
    "aec": true,
    "aec2": false,
    "ae_level": 0,
    "aec_value": 300,
    "agc": true,
    "agc_gain": 0,
    "gainceiling": 0,
    "bpc": false,
    "wpc": true,
    "raw_gma": true,
    "lenc": true,
    "hmirror": false,
    "vflip": false,
    "dcw": true,
    "colorbar": false
  }
}
```

Ordering is deliberate:

```text
ESP /stop (best-effort prior session)
→ ESP /config?<all settings>
→ ESP /start
→ PC /capture polling worker
```

No image is fetched before `/start` succeeds.

### `POST /api/camera/remote/stop`

Stops the PC pull worker first, then calls ESP `/stop`. Device connection remains configured.

### `POST /api/camera/remote/disconnect`

Stops the stream best-effort and clears the configured ESP connection.

## ESP V033 contract

ESP port 80:

- `GET /`
- `GET /status`
- `POST /config?<settings>`
- `POST /start`
- `POST /stop`
- `GET /capture`

ESP port 81:

- `GET /stream`

`/capture` and `/stream` reject requests while `session_active=false`.

## Existing compatibility

- `POST /api/camera/frame?source_id=<id>` remains supported.
- `GET /api/camera/frame` remains the common PC-side latest-frame surface.
- Camera simulation remains unchanged.
- Dataset/inference/zones/analytics consume the same CameraFrameService path.

No public-road signal-control API is introduced.
