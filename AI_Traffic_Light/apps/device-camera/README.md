# Device Camera App

This folder contains camera-node code and instructions.

The camera device is a **frame sender only**. The PC remains responsible for AI inference, detection/segmentation, training, GUI, dataset persistence, analytics, and traffic-light simulation/recommendation logic.

## Implemented camera node

`esp32-cam/` now contains a working PlatformIO sender for the common AI Thinker ESP32-CAM layout.

Its data path is:

```text
ESP32-CAM captures JPEG
→ Wi-Fi
→ HTTP POST raw JPEG
→ PC Studio /api/camera/frame?source_id=<camera_id>
```

The firmware includes Wi-Fi reconnect, camera reinitialization attempts, bounded HTTP timeouts, serial diagnostics, and a local `/status` endpoint.

See:

```text
apps/device-camera/esp32-cam/README.md
```

for configuration, wiring, flashing, and acceptance checks.

## Other possible camera sources

- Webcam connected directly to the PC.
- Phone/IP camera integration in a future receiver path.
- Additional ESP camera nodes after PC Studio gains per-source frame retention/routing.

## Important project rule

Do not move heavy training/inference onto the ESP camera node. Do not use this prototype as a public-road traffic controller.
