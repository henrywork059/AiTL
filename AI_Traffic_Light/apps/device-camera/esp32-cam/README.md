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

When PSRAM exists the camera initializes JPEG at UXGA with two PSRAM framebuffers and `CAMERA_GRAB_LATEST`, then applies the PC-selected runtime resolution. Wi-Fi sleep is disabled. The stream uses `TCP_NODELAY`, keepalive and a short send deadline.

If a frame cannot be delivered promptly, the ESP closes the stream socket rather than allowing old frames to build up. PC Studio reconnects and resumes from current imagery.

## Compatibility

PC Studio's current binary stream requires compatible firmware. V035 HTTP/MJPEG firmware is rejected during Connect; V036 binary TCP remains accepted during migration because it uses the same `aitl-tcp-jpeg-v1` wire format.

Legacy `POST /api/camera/frame` remains available in PC Studio for other device senders, but this ESP firmware no longer uses per-frame HTTP uploads.

## Prototype boundary

This camera node only supplies images to the local AiTL prototype. It performs no heavy inference and has no public-road traffic-signal authority.

### V037 adaptive transport
V037 keeps the V036 `ATL1` TCP wire format and R6 vectored non-blocking sender, then adds adaptive JPEG pressure control. The saved/user-configured JPEG quality remains the quality floor. When send time exceeds the target-frame budget, frames are large, or a send fails, firmware temporarily increases the OV2640 JPEG quality number (stronger compression) up to a bounded ceiling. After a sustained run of small/fast frames, it steps back toward the configured quality. Status/serial telemetry exposes configured/effective quality, adjustment count, and send-time EWMA.

New profiles default to QVGA / JPEG 24 / 15 FPS; existing saved profiles are preserved. V037 PC Studio remains wire-compatible with V036 camera nodes during migration, but V037 adaptive behavior requires flashing the V037 firmware.
