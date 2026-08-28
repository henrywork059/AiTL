# Start Here — V036

V036 / `0_3_6` is the current unaccepted candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Camera transport

```text
ESP boot → idle
PC Connect → GET /status only → zero image bytes

PC Start Stream
  → POST /stop
  → POST /config (full OV2640 settings + target FPS)
  → POST /start
  → TCP connect to ESP :81
  → [ATL1 | JPEG length | sequence | ESP uptime] + JPEG
  → CameraFrameService
      ├─ PC browser MJPEG relay
      ├─ Live AI
      ├─ Dataset Capture
      ├─ Zones
      └─ analytics
```

HTTP is deliberately retained for low-rate control/status. The high-rate ESP→PC image path is no longer HTTP/MJPEG.

If the image socket fails, PC Studio probes `/status`. A still-active ESP session is reconnected directly; a lost/rebooted session receives `/config` + `/start` before reconnection.

Flash the matching V036 firmware before testing. V036 PC Studio rejects V035 firmware because port 81 carries a different wire protocol.
