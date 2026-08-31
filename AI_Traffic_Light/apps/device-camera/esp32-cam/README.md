# AiTL ESP32-CAM camera node

This folder contains the AI Thinker ESP32-CAM firmware used by PC Studio.

The production architecture remains PC-initiated:

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
- Frame format: 16-byte `ATL1` header (`length`, `sequence`, `uptime_ms`) followed by the complete JPEG.
- Browser preview is produced by PC Studio; browsers never connect directly to port 81.

V0310 keeps this wire format deliberately so the existing PC receiver and saved multi-camera profiles remain compatible.

## PlatformIO

The checked-in target uses:

```ini
board = esp32cam
framework = arduino
build_src_filter = +<main_v0310.cpp>
```

`src/main_v0310.cpp` wraps the mature session implementation and applies the current R10-backed production tuning.

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

The V0310 production sketch is:

```text
arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino
```

Keep the sketch inside the full pulled repository because it intentionally reuses the adjacent V037 implementation instead of duplicating the mature control/session code. Copy its `secrets.example.h` to `secrets.h`, enter Wi-Fi credentials, then upload as an **AI Thinker ESP32-CAM** target using the installed ESP32 Arduino core.

The separate `arduino/AiTL_ESP32_CAM_ARCH_DIAG/` sketch is the R10 diagnostic benchmark; it is not the production firmware.

## Production defaults and saved settings

New-camera defaults remain:

```text
320 × 240 (QVGA)
JPEG quality 24
15 FPS requested target
```

PC Studio `/config` remains authoritative, so an existing saved profile continues to control resolution, JPEG quality and target FPS. V0310 does not silently force the R10 diagnostic q18 recommendation.

## V0310 low-latency behavior

R10 physical testing in a strong-Wi-Fi position compared framebuffer count/grab mode, target FPS, newest-frame caching, JPEG quality and TCP write sizing. V0310 applies only the findings that can be moved into production without changing the wire/API contract:

- one framebuffer is retained;
- the PSRAM path uses `CAMERA_GRAB_LATEST` for freshness;
- the inherited bounded sender uses plain non-blocking `send()` rather than a real vectored `sendmsg()` hot path;
- each application send is capped at 11,680 bytes, the best raw-TCP write size in the R10 sweep;
- TCP/lwIP remains responsible for packet segmentation;
- `TCP_NODELAY`, keepalive, bounded no-progress/total-send limits and deterministic failed-frame socket close remain active;
- the scheduler never queues catch-up work;
- PC Studio reconnect/session recovery remains unchanged;
- configured JPEG quality and resolution are never changed automatically because of network pressure.

The Pi-style newest-frame cache is not part of production V0310 because the R10 strong-Wi-Fi run showed no matched-target FPS improvement over direct capture/send.

## Physical performance target

The R10 diagnostic reached 12.43 FPS at a 15 FPS target in the good Wi-Fi position. That value belongs to the diagnostic path and is not automatically a production result.

After flashing V0310, test the real Camera Sources path at the same location. A useful candidate target is approximately 10–12 FPS sustained with complete JPEGs, no sustained send-deadline failure loop, no unexpected reconnect churn, and unchanged configured image quality/resolution.

If the production ATL1 path remains materially slower than the R10 camera ladder, the next comparison should isolate ATL1 framing/PC receiving versus the diagnostic HTTPD path rather than adding framebuffer/cache complexity.

## Telemetry

Status and Serial Monitor expose actual FPS, frame bytes, capture/send time, send EWMA, slow-frame count, RSSI, BSSID, channel and Wi-Fi disconnect/reconnect counters. The V0310 Arduino/PlatformIO entrypoint also prints an explicit `AiTL V0310 R10-tuned production pipeline active` startup marker.

Legacy R2/R4 adaptive telemetry keys remain zero-valued for compatibility with existing PC Studio surfaces.

## Compatibility

The production HTTP identity remains V037-compatible while the wire stream remains `aitl-tcp-jpeg-v1` / `ATL1`. V036 binary TCP remains accepted during migration because it uses the same stream format. V035 HTTP/MJPEG production firmware is not compatible with the current binary receiver.

Legacy `POST /api/camera/frame` remains available in PC Studio for other device senders, but this ESP firmware does not use per-frame HTTP uploads.

## Prototype boundary

This camera node only supplies images to the local AiTL prototype. It performs no heavy inference and has no public-road traffic-signal authority.
