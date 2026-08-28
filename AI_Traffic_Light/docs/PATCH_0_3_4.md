# Patch 0_3_4 — Low-latency ESP MJPEG transport

## Release state

- Candidate: V034 / `0_3_4`
- Previous candidate: V033 / `0_3_3`
- Passed baseline: V024 / `0_2_4`

## Main performance change

V033:

```text
GET /capture
close HTTP
wait
GET /capture
close HTTP
...
```

V034:

```text
GET :81/stream
└── continuous multipart JPEG frames over one connection
```

This removes per-frame HTTP connection overhead and reduces the chance of processing delayed/stale snapshots.

## PC-side changes

- persistent MJPEG reader;
- JPEG SOI/EOI extraction across arbitrary network chunk boundaries;
- newest frame enters the existing CameraFrameService immediately;
- automatic stream reconnect after transient disconnect;
- active socket is closed on Stop Stream for bounded shutdown;
- simulation pauses ESP image transport and reopens it afterward;
- status reports target/measured FPS, frame interval, bytes and reconnect count;
- `/api/camera/live.mjpeg` provides low-latency browser preview;
- old V033 `fetch_interval_ms` start calls remain accepted and are mapped to target FPS.

## ESP-side changes

- accepts `stream_fps` 1–30 in `/config`;
- keeps Wi-Fi sleep disabled;
- keeps `CAMERA_GRAB_LATEST`;
- keeps two PSRAM framebuffers;
- caps MJPEG frame production at the PC-selected FPS;
- keeps V033 idle-session gating: no image response before `/start`.

## Recommended first settings

- VGA
- JPEG quality 12–16
- 15 FPS

Try 20 FPS on a strong 2.4 GHz link. If latency worsens or reconnects rise, reduce resolution/FPS or increase JPEG quality number to reduce frame size.
