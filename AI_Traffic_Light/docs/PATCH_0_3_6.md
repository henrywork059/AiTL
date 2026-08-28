# Patch 0_3_6 — Low-latency binary TCP ESP streaming

## Release state

- Candidate: V036 / `0_3_6`
- Previous candidate: V035 / `0_3_5`
- Passed baseline: V024 / `0_2_4`

This is a new performance patch requested by the owner, so Z increments by one. The passed baseline is not promoted.

## Why V035 was not the end state

V035 already fixed most obvious MJPEG problems: persistent connection, `TCP_NODELAY`, keepalive, exact `Content-Length`, newest-frame handling, event-driven browser wakeups and recovery. Online comparison with current Espressif sources confirms those camera fundamentals are sound.

Two remaining costs were AiTL-specific:

1. ESP→PC still wrapped every JPEG in HTTP multipart framing even though the only consumer is PC Studio.
2. A slow TCP send could keep an old frame alive for seconds, which is undesirable for real-time perception even if eventual delivery succeeds.

The repository also contained an older PlatformIO `main.cpp` that still opened a new HTTP upload for every frame, while current backend/docs described PC-pull streaming. V036 removes that split implementation.

## V036 wire protocol

Port 80 remains HTTP control/status. Port 81 becomes one persistent binary TCP JPEG stream.

Each source frame is:

```text
Offset  Size  Field
0       4     ASCII magic "ATL1"
4       4     JPEG byte length, unsigned network-endian uint32
8       4     source sequence, unsigned network-endian uint32
12      4     ESP uptime milliseconds, unsigned network-endian uint32
16      N     JPEG bytes
```

There is no per-frame JSON, HTTP header, multipart boundary or chunked-transfer wrapper in the ESP→PC hot path.

The browser still receives `/api/camera/live.mjpeg` from PC Studio. No frontend/browser protocol migration is required.

## Freshness policy

V036 is deliberately freshness-first:

- `CAMERA_GRAB_LATEST` and two PSRAM framebuffers remain enabled when PSRAM exists;
- camera allocation initializes at UXGA before applying the lower PC-selected runtime resolution;
- frame cadence uses deadline scheduling, so capture/send time is not added on top of the requested FPS interval;
- the stream socket uses `TCP_NODELAY` and keepalive;
- ESP socket send timeout is short;
- the complete header+JPEG has a bounded frame-send deadline;
- if that deadline is missed, the ESP closes the client instead of queuing stale visual history;
- PC Studio reconnects with bounded exponential backoff and restores a lost ESP session when necessary.

This design may intentionally reconnect on severe Wi-Fi congestion. That is preferable to displaying seconds-old traffic imagery.

## PC receiver changes

The Python receiver now:

- opens a raw TCP socket directly to port 81;
- uses exact 16-byte header and exact payload reads;
- uses `recv_into` on the real socket path;
- validates magic, length and JPEG SOI/EOI;
- tracks source sequence gaps and source uptime;
- uses a 2 s stream stall timeout instead of V035's 6 s tolerance;
- retains event-driven wakeups for the browser relay;
- retains simulation pause/resume and automatic session recovery;
- rejects V035/other mismatched firmware during Connect with a clear compatibility error.

## Firmware normalization

`apps/device-camera/esp32-cam/src/main.cpp` is rewritten to match the current PC-controlled architecture. It no longer requires the PC/server IP and no longer POSTs one JPEG per HTTP request.

A standalone Arduino IDE sketch is also included at:

`apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V036/AiTL_ESP32_CAM_V036.ino`

Only Wi-Fi credentials are required on the ESP. PC Studio owns the ESP IP entry.

## Deliberate non-changes

- PC→browser preview remains MJPEG.
- AI/inference remains on the PC.
- simulation, capture, training, zones and analytics continue to use `CameraFrameService`.
- no independent simultaneous multi-camera frame store is added.
- no public-road traffic controller authority is added.

## Expected performance effect

The patch removes hot-path HTTP/multipart parsing and prevents multi-second blocked sends from becoming stale-frame latency. Actual FPS is still bounded by OV2640 JPEG capture time, selected resolution/quality, ESP32 CPU/PSRAM behavior and 2.4 GHz Wi-Fi conditions. It is therefore expected to improve transport overhead and worst-case latency, not to guarantee a fixed FPS increase on every network.
