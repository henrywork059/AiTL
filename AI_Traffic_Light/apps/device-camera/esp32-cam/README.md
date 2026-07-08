# ESP32-CAM Firmware Placeholder

This is a placeholder for the ESP32-CAM camera sender firmware.

## First firmware goal

```text
ESP32-CAM connects to Wi-Fi
→ starts camera
→ hosts MJPEG stream
→ PC reads stream URL
```

Example target stream URL:

```text
http://<esp32-cam-ip>:81/stream
```

## Development options

You can use either:

- Arduino IDE
- PlatformIO

This skeleton contains a PlatformIO-style folder, but the firmware is intentionally incomplete at this stage.

## Planned controls

- Set resolution.
- Set JPEG quality.
- Restart stream.
- Show device status.
- Add camera ID.

## Important project rule

Do not run heavy AI on the ESP32-CAM. The PC should do AI inference.
