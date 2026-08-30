# Camera transport isolation test — 0_3_8 R3

This is a **diagnostic-only** test for the physical ESP32-CAM transport fault. It deliberately does not change the normal V037 production sender before the cause is proven.

## What it tests

The suite keeps the same OV2640 camera and Wi-Fi link while changing only the delivery path:

1. one HTTP `/capture` JPEG;
2. finite HTTP MJPEG at the selected FPS;
3. ATL1 direct camera-framebuffer send with a 1200 ms stall / 2000 ms total limit;
4. ATL1 direct camera-framebuffer send with a relaxed 5000 ms stall / 7000 ms total limit;
5. ATL1 real JPEG staged through internal DRAM chunks (default 1460 B);
6. ATL1 exact real JPEG copied fully into internal DRAM before sending;
7. ATL1 synthetic internal-DRAM payload with the same byte size as the HTTP reference JPEG;
8. optional staged chunk sweep: 256 / 512 / 1024 / 1460 / 2920 B.

The ESP records `last_send_ms`, accepted bytes, errno, free internal RAM/PSRAM, RSSI/BSSID/channel, and accepted-byte progress checkpoints.

## Why this separates the likely causes

- `/capture PASS + MJPEG PASS + direct 1200 FAIL + direct 5000 PASS` → the current bounded timeout is materially involved, although multi-second send latency is still abnormal.
- `/capture PASS + MJPEG PASS + direct 5000 FAIL + staged PASS + full-JPEG-DRAM PASS + synthetic PASS` → direct PSRAM camera framebuffer → `sendmsg()` is the leading cause.
- `synthetic FAIL` → do not blame PSRAM first; investigate general lwIP/Wi-Fi/socket/receiver behavior.
- `capture PASS + MJPEG FAIL` → persistent streaming/backpressure is implicated before ATL1 framing.
- `/capture FAIL` → investigate camera/power/framebuffer before transport.

## Run

1. In Arduino IDE open:

   `apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_TRANSPORT_DIAG/AiTL_ESP32_CAM_TRANSPORT_DIAG.ino`

2. Copy `secrets.example.h` to `secrets.h` in that sketch folder and enter the same 2.4 GHz Wi-Fi credentials.
3. Board: **AI Thinker ESP32-CAM**. Upload the diagnostic sketch.
4. Open Serial Monitor at 115200 and note the ESP IP.
5. From the AiTL project root run:

```powershell
python .\scripts\test_camera_transport_isolation.py --host 192.168.1.87 --frames 6 --fps 5
```

For the chunk-size sweep:

```powershell
python .\scripts\test_camera_transport_isolation.py --host 192.168.1.87 --frames 6 --fps 5 --chunk-sweep
```

Replace `192.168.1.87` with the actual ESP address.

The script prints a compact table and writes `camera_transport_isolation.json`. Send that JSON/report output back for diagnosis.

## After the test

Reflash the normal AiTL V037 firmware before returning to PC Studio. This diagnostic sketch is not the production camera node and does not authorize or control physical/public-road traffic signals.
