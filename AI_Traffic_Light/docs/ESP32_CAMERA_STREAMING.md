# ESP32-CAM V034 streaming

Use the matching `AiTL_ESP32CAM_V034_ArduinoIDE.zip`.

## Transport

The ESP remains idle after boot and Connect. Start Stream sends camera settings plus `stream_fps`, calls `/start`, then PC Studio opens one persistent:

```text
http://<ESP-IP>:81/stream
```

No continuous image traffic exists while idle.

## Performance settings

Recommended baseline:

```text
VGA
JPEG quality 12–16
15 FPS
```

For lower latency/bandwidth:
- use QVGA/VGA rather than UXGA;
- use a higher JPEG quality number (for example 14–18) to reduce byte size;
- use 10–15 FPS on weaker Wi-Fi;
- try 20 FPS only when RSSI/stability are good.

The firmware keeps Wi-Fi sleep disabled and uses `CAMERA_GRAB_LATEST` so stale queued frames are not preferred.

## Simulation

When PC Studio simulation starts, the backend closes/pauses its ESP stream request. The ESP session remains configured but sends no image bytes because no stream client is requesting them. PC Studio reopens the MJPEG stream after simulation stops.
