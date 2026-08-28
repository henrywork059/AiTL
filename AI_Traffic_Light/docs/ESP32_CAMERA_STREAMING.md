# ESP32-CAM low-latency streaming

## Current architecture

The camera node is intentionally simple: capture JPEGs and deliver them to PC Studio. AI, dataset handling, training, analytics and signal simulation remain on the PC.

```text
Port 80: HTTP /status /config /start /stop /capture
Port 81: one persistent AiTL TCP JPEG stream per ESP
```

Connect is control-only. The ESP does not send image bytes until PC Studio applies settings, calls `/start`, and opens port 81.

## Image framing

The port-81 stream uses a fixed 16-byte network-endian header followed immediately by JPEG bytes:

`ATL1 + length + sequence + uptime_ms + JPEG`

The fixed header avoids multipart boundary scanning and per-frame HTTP headers between ESP and PC.

## Camera configuration

When PSRAM exists, initialize JPEG capture at UXGA, quality 10, two PSRAM framebuffers and `CAMERA_GRAB_LATEST`, then apply the lower runtime resolution/quality selected in PC Studio. This preserves sufficient framebuffer allocation for later resolution changes.

Recommended first physical settings:

```text
Resolution: VGA
JPEG quality: 14
Target FPS: 15
```

Test 20 FPS after 15 FPS is stable. Use QVGA or a larger JPEG-quality number if bandwidth/capture time is limiting.

## Latency controls

- Wi-Fi sleep disabled.
- `TCP_NODELAY` enabled.
- TCP keepalive enabled.
- no application image queue on the ESP.
- frame schedule is based on target deadlines rather than `delay()` after a send.
- blocked frame sends use a 250 ms no-progress timeout plus a 500 ms hard whole-frame cap.
- missed deadline closes the client; PC Studio reconnects to fresh imagery.
- PC receiver declares a 2 s source stall instead of waiting 6 s.

## Firmware choices

PlatformIO source:

`apps/device-camera/esp32-cam/src/main.cpp`

Standalone Arduino IDE sketch:

`apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V036/AiTL_ESP32_CAM_V036.ino`

For either workflow, configure only the ESP Wi-Fi credentials. Do not configure a PC IP on the ESP. PC Studio asks for the ESP's private-LAN IPv4 address.


## Multiple ESP cameras

PC Studio can save up to 12 ESP camera profiles. Each profile retains its private-LAN IPv4 address, source ID, target FPS and complete OV2640 settings. The last-selected camera is restored when PC Studio restarts.

Each connected/started ESP has its own independent port-81 TCP worker and newest-frame cache. Multiple ESP streams can remain active at the same time. The Camera Sources page selects which source is forwarded into `CameraFrameService`; non-selected streams are received/cached but cannot overwrite the active AI/capture frame. Switching to an already-running ESP promotes its cached newest frame only when it is recent and then follows live frames. If the cache is stale, PC Studio clears the previous physical source and waits for a fresh frame instead of re-stamping old JPEG bytes as new.

Simulation still pauses all physical ESP image transports and they resume automatically afterward.

## V036 send-path behavior

The ESP stream socket uses TCP_NODELAY/keepalive plus a progress-bounded non-blocking send loop. JPEG data is offered in 1360-byte chunks with `send(..., MSG_DONTWAIT)`. Temporary `EAGAIN` backpressure is handled with short `select()` waits; every successful partial write resets a 250 ms no-progress timer. A separate 500 ms whole-frame ceiling prevents indefinite stalls. If progress stops or the hard cap is reached, the socket is closed and the PC reconnects to a fresh frame rather than preserving a stale/partial image.
