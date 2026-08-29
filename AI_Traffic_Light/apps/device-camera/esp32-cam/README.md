# AiTL ESP32-CAM camera node

This folder contains the AI Thinker ESP32-CAM firmware used by PC Studio.

The current architecture is PC-initiated:

```text
ESP boot → Wi-Fi → idle
PC Studio Connect → ESP /status only
PC Studio Start → /config → /start → persistent TCP JPEG stream
PC Studio Stop → close stream → /stop
```

The ESP does **not** need the PC's IP address. It only needs its own Wi-Fi credentials. In PC Studio, enter the ESP's private-LAN IPv4 address.

## Transport

- HTTP port 80: `/status`, `/config`, `/start`, `/stop`, optional idle `/capture`.
- TCP port 81: one low-latency binary JPEG stream.
- Frame format: 16-byte `ATL1` header (`length`, `sequence`, `uptime_ms`) followed by the JPEG.
- Browser preview is produced by PC Studio; browsers never connect directly to port 81.

## PlatformIO

The checked-in target is:

```ini
board = esp32cam
framework = arduino
```

Create the local secret file:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\device-camera\esp32-cam"
Copy-Item .\include\secrets.example.h .\include\secrets.h
```

Edit only the Wi-Fi values in `include/secrets.h`.

Build/upload:

```powershell
pio run
pio run -t upload
pio device monitor -b 115200
```

## Arduino IDE

A standalone sketch is provided at:

```text
arduino/AiTL_ESP32_CAM_V037/AiTL_ESP32_CAM_V037.ino
```

Copy `secrets.example.h` to `secrets.h` inside that sketch folder, enter Wi-Fi credentials, then upload as an **AI Thinker ESP32-CAM** target using the installed ESP32 Arduino core.

## First physical test

Use for a new V037 profile:

```text
320 × 240 (QVGA)
JPEG quality 24
15 FPS
```

Expected Serial output includes the ESP IP, stream client state, actual FPS, frame bytes, capture time and send time. Test 20 FPS only after 15 FPS is stable.

## Low-latency behavior

When PSRAM exists, R6 allocates one UXGA-capable PSRAM framebuffer with `CAMERA_GRAB_WHEN_EMPTY`, keeps the 20 MHz camera clock, then applies the PC-selected runtime resolution and JPEG quality. This keeps runtime size changes available without the continuous two-buffer `CAMERA_GRAB_LATEST` pipeline used by R4.

The stream keeps `TCP_NODELAY`, keepalive and progress-bounded non-blocking vectored sends. A slow link lowers achieved FPS naturally because the scheduler never queues catch-up work. If a partial ATL1 frame times out, the ESP closes that client socket and waits for PC Studio to reconnect. The saved JPEG quality and resolution are not changed as a network-pressure response.

Status and Serial Monitor expose send EWMA, slow-frame count, RSSI, BSSID, channel and Wi-Fi disconnect/reconnect counters. Legacy R2/R4 adaptive telemetry keys remain zero-valued for same-candidate compatibility.

## Compatibility

PC Studio's current binary stream requires compatible firmware. V035 HTTP/MJPEG firmware is rejected during Connect; V036 binary TCP remains accepted during migration because it uses the same `aitl-tcp-jpeg-v1` wire format.

Legacy `POST /api/camera/frame` remains available in PC Studio for other device senders, but this ESP firmware no longer uses per-frame HTTP uploads.

## Prototype boundary

This camera node only supplies images to the local AiTL prototype. It performs no heavy inference and has no public-road traffic-signal authority.

### V037 R6 quality-preserving transport

Physical isolation tests showed that the camera can capture stably with one `CAMERA_GRAB_WHEN_EMPTY` buffer at 20 MHz, and that TCP can carry 8/16/32 KiB framed payloads without treating the lwIP send buffer as a maximum frame size. R6 therefore removes the ~5 KB payload target, partial-send target learning, q=50 escalation, local oversize rejection and effective-resolution downshift. New profiles remain QVGA / JPEG 24 / 15 FPS; existing saved profiles are preserved.
