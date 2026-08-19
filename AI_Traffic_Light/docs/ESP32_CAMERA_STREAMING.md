# ESP32-CAM streaming integration

## Purpose

Provide a real hardware camera input for AiTL using the camera receiver that already exists in PC Studio.

The implementation uses repeated raw-JPEG HTTP uploads rather than making PC Studio pull an MJPEG URL:

```text
ESP32-CAM
  capture JPEG
      |
      v
POST /api/camera/frame?source_id=esp32_cam_01
Content-Type: image/jpeg
      |
      v
PC Studio latest-frame receiver
```

This matches the existing backend contract and keeps the ESP firmware small.

## Network requirements

- ESP and PC must be able to reach each other on the same LAN or otherwise routable private network.
- PC Studio backend listens on TCP port 8000 in the normal Windows launcher.
- `AITL_SERVER_HOST` must be the PC's LAN address, not `127.0.0.1`.
- Windows Firewall may need a Private-network inbound allowance for the Python/Uvicorn backend.

## Firmware configuration

Private/local settings live in:

```text
apps/device-camera/esp32-cam/include/secrets.h
```

That file is ignored by the device-camera `.gitignore` and should not be uploaded to GitHub.

The committed template is:

```text
apps/device-camera/esp32-cam/include/secrets.example.h
```

## Data contract

Firmware sends:

```http
POST /api/camera/frame?source_id=<id>
Content-Type: image/jpeg
X-AiTL-Device: <id>

<raw JPEG bytes>
```

No base64 or multipart wrapper is used. The existing backend validates the image and returns its standard JSON success/error envelope.

## Diagnostics

Serial monitor: `115200` baud.

ESP local status endpoint:

```text
GET http://<ESP-IP>/status
```

Key fields include Wi-Fi state, camera state, upload/failure counts, last HTTP status, last frame size/upload time, RSSI, heap, and uptime.

Useful HTTP interpretation:

- `2xx`: frame accepted.
- `404`: wrong backend route/port.
- `415`: wrong content type; firmware should always send JPEG.
- `422`: source ID/image validation failed.
- negative HTTPClient result: connection/DNS/socket failure; check PC IP, backend, Wi-Fi, and firewall.

## Current multi-camera limitation

The backend currently keeps one latest uploaded device frame, not one frame per `source_id`. Multiple senders can identify themselves, but simultaneous devices will overwrite the single latest-device-frame slot. Add per-source retention/routing before treating two ESP cameras as independent live PC Studio sources.

## Safety boundary

This is a local/student prototype camera transport. It must not be described as a production or public-road traffic-control camera/control system.
