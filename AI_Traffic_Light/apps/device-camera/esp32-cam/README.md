# AiTL ESP32-CAM live frame sender

This folder contains the first working ESP32-CAM sender for AiTL.

The firmware is intentionally a lightweight camera node:

```text
AI Thinker ESP32-CAM
→ Wi-Fi
→ capture JPEG
→ POST raw JPEG to PC Studio
→ /api/camera/frame?source_id=<device_id>
```

The PC remains responsible for inference, dataset capture, training, analytics, and all traffic-light simulation/recommendation logic.

## Supported target

The checked-in PlatformIO environment uses:

```ini
board = esp32cam
framework = arduino
```

`src/main.cpp` therefore uses the standard **AI Thinker ESP32-CAM** camera pin map. If your camera board is an ESP32-S3 camera or another pin layout, do not flash this pin map unchanged.

## 1. Create the local secrets file

From:

```text
AI_Traffic_Light/apps/device-camera/esp32-cam/
```

copy:

```text
include/secrets.example.h
```

to:

```text
include/secrets.h
```

`include/secrets.h` is ignored by Git.

Edit at least:

```cpp
#define AITL_WIFI_SSID "YOUR_WIFI_NAME"
#define AITL_WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define AITL_SERVER_HOST "192.168.1.100"
#define AITL_SOURCE_ID "esp32_cam_01"
```

Use the PC's **LAN IPv4 address** for `AITL_SERVER_HOST`. On Windows, run:

```powershell
ipconfig
```

Use the IPv4 address for the Wi-Fi/Ethernet adapter that is on the same LAN as the ESP. Do not enter `127.0.0.1` and do not include `http://`.

The normal AiTL backend port is `8000`.

## 2. Start PC Studio backend

The repository's Windows backend launcher already binds to `0.0.0.0:8000`, which allows another device on the LAN to reach it.

Start the backend using the normal AiTL workflow. If Windows Firewall asks, allow Python/Uvicorn on the **Private** network used by the prototype.

Before flashing the ESP, test from another device on the same LAN if possible:

```text
http://<PC-LAN-IP>:8000/api/camera/status
```

A JSON response confirms that the PC is reachable.

## 3. Build and upload with PlatformIO

Open this folder in VS Code with the PlatformIO extension, or run:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\device-camera\esp32-cam"
pio run
pio run -t upload
pio device monitor -b 115200
```

If `pio` is not available in a normal PowerShell terminal, use the PlatformIO VS Code toolbar commands **Build**, **Upload**, and **Serial Monitor**.

### Bare AI Thinker ESP32-CAM + USB-to-TTL

Typical programming wiring:

```text
USB-TTL 5V  -> ESP32-CAM 5V
USB-TTL GND -> ESP32-CAM GND
USB-TTL TX  -> ESP32-CAM U0R / GPIO3
USB-TTL RX  -> ESP32-CAM U0T / GPIO1
ESP32-CAM GPIO0 -> GND only while entering flash mode
```

Use a USB-to-TTL adapter with **3.3 V serial logic**. Power the ESP32-CAM through its 5 V input with a supply/adapter that can provide stable current. After upload, disconnect GPIO0 from GND and reset/power-cycle the board to boot normally.

An ESP32-CAM-MB programmer board normally handles the serial wiring for you.

## 4. Expected serial output

A working boot should show messages similar to:

```text
AiTL ESP32-CAM live frame sender
Camera ready ...
Wi-Fi connected. ESP IP: 192.168.x.x
Receiver: http://192.168.x.x:8000/api/camera/frame?source_id=esp32_cam_01
Frame upload OK ...
```

The ESP also exposes a local diagnostic endpoint:

```text
http://<ESP-IP>/status
```

It reports camera/Wi-Fi state, upload counters, last HTTP result, RSSI, heap, and uptime. It does not expose the Wi-Fi password.

## 5. PC Studio acceptance check

With simulation mode stopped:

1. Open **Camera Sources** in PC Studio.
2. Power the ESP32-CAM.
3. Confirm the camera status changes to the configured `source_id`.
4. Confirm frame number continues increasing.
5. Confirm the preview shows the real ESP image.
6. Leave it running for at least 2 minutes and confirm uploads continue after normal Wi-Fi jitter.
7. Temporarily stop the backend, wait for upload failures on Serial Monitor, restart the backend, and confirm uploads recover without rebooting the ESP.

## Default streaming settings

```text
Resolution: VGA / 640x480 when PSRAM is available
JPEG quality: 12
Upload interval: 250 ms (up to about 4 frames/s)
HTTP timeout: 3.5 s
```

If the link is unstable, first increase `AITL_FRAME_INTERVAL_MS` to `500UL`. If necessary, reduce `AITL_FRAME_SIZE` to `FRAMESIZE_QVGA`.

## Current limitation

PC Studio's current receiver retains one latest uploaded device frame. `source_id` identifies the sender, but two ESP cameras uploading at the same time will currently replace each other's latest frame. Multi-camera retention/routing needs a later PC-side change.

## Prototype boundary

This firmware only sends camera images to the local AiTL PC prototype. It does not run heavy AI and does not control public-road traffic infrastructure.
