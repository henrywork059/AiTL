# Start Here — V037

V037 / `0_3_7` is the current unaccepted candidate. V036 / `0_3_6` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Camera transport

```text
PC Connect -> ESP /status only
PC Start -> /config -> /start -> persistent TCP :81
ESP -> ATL1 header + JPEG
    -> V037 R2 single-window adaptive JPEG controller
    -> per-ESP newest-frame cache
selected ESP -> CameraFrameService -> preview / Live AI / capture / zones / analytics
```

V037 keeps the V036 `aitl-tcp-jpeg-v1` wire format. V037 firmware reports `aitl-camera-v037`; PC Studio also accepts V036 binary-TCP nodes while cameras are being reflashed.

For new profiles start at **320 × 240, JPEG 24, 15 FPS**. V037 R2 first tries to keep JPEG payloads near 5 KB so one ATL1 frame can usually fit a single ESP TCP send window. Oversized captures are compressed and skipped locally before they can create a partial TCP frame; quality recovers slowly when there is clear payload headroom.

Saved multi-ESP profiles remain runtime user data in `config/remote_cameras.json` and are not replaced by the patch.
