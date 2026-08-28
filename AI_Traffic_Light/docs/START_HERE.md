# Start Here — Current V032 candidate

Root `VERSION` is authoritative. V032 / `0_3_2` is the current unaccepted candidate. V031 / `0_3_1` is the previous candidate because the owner explicitly requested V032 before separately accepting V031. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## What V032 changes

V032 connects the physical ESP32-CAM to the existing PC-side camera pipeline without requiring the ESP firmware to know the PC address.

The tested Arduino baseline is the stock ESP32 `CameraWebServer` example. PC Studio now accepts the ESP private-LAN IPv4 address and uses:

```text
GET http://<ESP-IP>/capture
GET http://<ESP-IP>:81/stream
```

The backend continuously pulls JPEG snapshots from `/capture` and stores them through the existing `CameraFrameService`. This means the same latest-frame path remains available to Live AI, Dataset Capture, Zone Editor, inference, tracking and traffic analytics.

## Camera architecture

```text
OV2640
  ↓
ESP32-CAM + stock Arduino CameraWebServer
  ├── /capture
  └── :81/stream
          ↓
AiTL PC Studio remote-camera service
          ↓
CameraFrameService
          ↓
inference / capture / zones / analytics / traffic-state prototype pipeline
```

The ESP does not need a configured PC IP.

## Safety / network guard

The backend accepts only literal RFC1918 private IPv4 addresses:

- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

This keeps the remote fetch feature scoped to a local prototype LAN and avoids making the backend a general URL fetcher.

## Simulation coexistence

If the built-in Camera Sources simulation is started while an ESP camera is configured, remote ingestion pauses. The ESP connection remains configured and ingestion resumes after simulation stops.

## Backward compatibility

The existing device push route remains:

```text
POST /api/camera/frame?source_id=<camera_id>
```

V032 does not remove the old ESP/Raspberry-Pi upload path.

## Limitations

- Remote camera configuration is process-memory only in this patch; reconnect after backend restart.
- The live backend still retains one latest non-simulation frame, not independent simultaneous per-camera buffers.
- Stock CameraWebServer direct MJPEG is used for Camera Sources preview; the backend uses repeated `/capture` snapshots for the shared processing pipeline.
- V032 does not add signal-output hardware control.
- Physical/public-road traffic-light authority remains outside scope.

## Validation starting point

Read:

1. `docs/PATCH_0_3_2.md`
2. `docs/ESP32_CAMERA_STREAMING.md`
3. `scripts/test_remote_camera_pull.py`

Then run the complete repository test workflow on the owner Windows checkout before acceptance.
