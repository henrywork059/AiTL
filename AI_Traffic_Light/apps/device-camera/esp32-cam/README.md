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
arduino/AiTL_ESP32_CAM_V036/AiTL_ESP32_CAM_V036.ino
```

Copy `secrets.example.h` to `secrets.h` inside that sketch folder, enter Wi-Fi credentials, then upload as an **AI Thinker ESP32-CAM** target using the installed ESP32 Arduino core.

## First physical test

Use:

```text
VGA
JPEG quality 14
15 FPS
```

Expected Serial output includes the ESP IP, stream client state, actual FPS, frame bytes, capture time and send time. Test 20 FPS only after 15 FPS is stable.

## Low-latency behavior

When PSRAM exists the camera initializes JPEG at UXGA with two PSRAM framebuffers and `CAMERA_GRAB_LATEST`, then applies the PC-selected runtime resolution. Wi-Fi sleep is disabled. The stream uses `TCP_NODELAY`, keepalive and a short send deadline.

If a frame cannot be delivered promptly, the ESP closes the stream socket rather than allowing old frames to build up. PC Studio reconnects and resumes from current imagery.

## Compatibility

PC Studio's current binary stream requires matching firmware. A V035 HTTP/MJPEG firmware will be rejected during Connect instead of being interpreted as the V036 frame protocol.

Legacy `POST /api/camera/frame` remains available in PC Studio for other device senders, but this ESP firmware no longer uses per-frame HTTP uploads.

## Prototype boundary

This camera node only supplies images to the local AiTL prototype. It performs no heavy inference and has no public-road traffic-signal authority.

### V036 same-candidate send repair
The TCP JPEG sender uses `MSG_DONTWAIT` and 1360-byte chunks. When lwIP reports temporary backpressure, the firmware waits in short `select()` slices. Successful writes reset a 250 ms no-progress timer; a separate 500 ms hard frame cap prevents indefinite stalls. This allows JPEGs larger than one default lwIP send-buffer window to complete after ACK progress without allowing stale backlog to grow. Reflash the ESP after applying this repair; the wire protocol and PC IP workflow are unchanged.
