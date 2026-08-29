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

When PSRAM exists, R6 initializes JPEG capture at UXGA capability with one PSRAM framebuffer and `CAMERA_GRAB_WHEN_EMPTY`, then applies the runtime resolution/quality selected in PC Studio. Allocating the single buffer at UXGA preserves later resolution changes without keeping a two-buffer latest-frame pipeline continuously active.

Recommended first physical settings:

```text
Resolution: QVGA (320 × 240)
JPEG quality: 24
Target FPS: 15
```

Test 20 FPS after 15 FPS is stable. Use QVGA or a larger JPEG-quality number if bandwidth/capture time is limiting.

## Latency controls

- Wi-Fi sleep disabled.
- `TCP_NODELAY` enabled.
- TCP keepalive enabled.
- no application image queue on the ESP.
- frame schedule is based on target deadlines rather than `delay()` after a send.
- new TCP connections get three bounded warm-up frames (1000 ms no-progress / 1500 ms total), then steady-state sends use 500 ms no-progress / 900 ms total limits.
- missed deadline closes the client; PC Studio reconnects to fresh imagery.
- PC receiver declares a 2 s source stall instead of waiting 6 s.

## Firmware choices

PlatformIO source:

`apps/device-camera/esp32-cam/src/main.cpp`

Standalone Arduino IDE sketch:

`apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino`

For either workflow, configure only the ESP Wi-Fi credentials. Do not configure a PC IP on the ESP. PC Studio asks for the ESP's private-LAN IPv4 address.


## Multiple ESP cameras

PC Studio can save up to 12 ESP camera profiles. Each profile retains its private-LAN IPv4 address, source ID, target FPS and complete OV2640 settings. The last-selected camera is restored when PC Studio restarts.

Each connected/started ESP has its own independent port-81 TCP worker and newest-frame cache. Multiple ESP streams can remain active at the same time. The Camera Sources page selects which source is forwarded into `CameraFrameService`; non-selected streams are received/cached but cannot overwrite the active AI/capture frame. Switching to an already-running ESP promotes its cached newest frame only when it is recent and then follows live frames. If the cache is stale, PC Studio clears the previous physical source and waits for a fresh frame instead of re-stamping old JPEG bytes as new.

Simulation still pauses all physical ESP image transports and they resume automatically afterward.

## V037 R6 send-path behavior

The ESP stream socket uses TCP_NODELAY/keepalive plus a progress-bounded non-blocking send loop. The 16-byte `ATL1` header and JPEG payload are exposed to lwIP as one scatter/gather `sendmsg(..., MSG_DONTWAIT)` logical write, so TCP is free to segment JPEGs larger than one send buffer. Temporary `EAGAIN` backpressure is handled with short `select()` waits.

Each new TCP connection receives three bounded warm-up successes (1200 ms no-progress / 2000 ms total); steady-state limits are 700 ms no-progress / 1500 ms total. A partial-frame failure closes that socket so the PC can discard the incomplete ATL1 record and reconnect deterministically.

The camera uses one PSRAM framebuffer with `CAMERA_GRAB_WHEN_EMPTY` and a 20 MHz XCLK. A pending idle frame is discarded when a new TCP client connects. Scheduling is freshness-first: if a send takes longer than the requested frame interval, the next deadline starts from current time instead of catching up old work.

### Quality-preserving policy

R6 removes the R2/R4 ~5 KB payload target, partial-send window learning, q=50 compression escalation and runtime resolution downshift. Network pressure may reduce achieved FPS or force a socket reconnect, but it does not rewrite the configured JPEG quality or frame size. Serial and `/status` telemetry expose `q=<effective>/<configured>` (normally equal), send EWMA, slow-send count, RSSI, BSSID, channel, and ESP Wi-Fi disconnect/reconnect counters.
