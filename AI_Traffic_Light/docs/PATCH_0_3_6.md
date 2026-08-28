# Patch 0_3_6 — Low-latency binary TCP and multi-ESP streaming

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
- the shared downstream AI/capture frame store remains single-active-source, but V036 now adds independent per-ESP transport workers and newest-frame caches so multiple physical streams can stay active and be switched by the user.
- no public-road traffic controller authority is added.

## Expected performance effect

The patch removes hot-path HTTP/multipart parsing and prevents multi-second blocked sends from becoming stale-frame latency. Actual FPS is still bounded by OV2640 JPEG capture time, selected resolution/quality, ESP32 CPU/PSRAM behavior and 2.4 GHz Wi-Fi conditions. It is therefore expected to improve transport overhead and worst-case latency, not to guarantee a fixed FPS increase on every network.


## Same-candidate multi-camera extension

At the owner's request, V036 now supports multiple ESP32-CAM devices without promoting the version to V037.

- Added a persistent camera registry at runtime `config/remote_cameras.json` using the existing atomic JSON-store helper.
- Up to 12 profiles retain private IPv4 address, source ID, target FPS and full OV2640 settings, plus the last-selected camera.
- Added one independent `RemoteCameraService` / TCP worker per connected ESP and a newest-frame cache per source. Multiple ESP streams can remain active simultaneously.
- Added an explicit active-source selector. Only the selected ESP publishes into the existing `CameraFrameService`, preserving one unambiguous source for Live AI, Dataset Capture, zones and analytics.
- Switching to another running ESP promotes its cached newest frame only when that cache is recent, then follows live frames without stopping the previous ESP stream. A stale target cache leaves the shared physical frame empty until a fresh target frame arrives.
- Re-addressing a saved source retires the old session generation before the new IP becomes active; late frames from the retired worker are rejected even if they arrive after the profile/cache reset.
- Stop/Disconnect operations affect only the selected ESP. Removing a saved camera stops/disconnects that target only. Backend shutdown disconnects all camera sessions.
- Added save/select/delete camera-profile APIs and Camera Sources UI for New camera, saved-camera selection, Save, Connect, Start/Stop, Disconnect and Remove saved.
- Connection/socket state is deliberately not persisted across PC Studio restart; only addresses/settings/selection are restored.

- Same-candidate UI repair: Camera Sources now displays OV2640 resolution choices and fallback status as numeric pixel dimensions (for example `640 × 480`) instead of format aliases such as `VGA`; the internal firmware/API frame-size enum is unchanged.
