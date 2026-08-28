# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light simulation prototype.

## Current release state

Root `VERSION` is authoritative. V033 / `0_3_3` is the current unaccepted candidate. V032 / `0_3_2` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## V033 physical-camera workflow

```text
ESP boots and waits
      ↓
PC Studio Connect
      ↓ GET /status only
no image transfer
      ↓
user chooses camera settings in PC Studio
      ↓
Start Stream
      ↓
PC → /config → /start
      ↓
PC repeatedly calls /capture
      ↓
existing CameraFrameService pipeline
```

Stop Stream stops PC frame requests and calls `/stop` on the ESP. The ESP remains reachable for status/control but image endpoints stay idle until the next PC start.

Camera settings are PC-owned for each stream start: resolution, JPEG quality, image adjustments, white balance, exposure, gain, corrections, mirror/flip/downsize/color-bar controls, and PC capture interval.

Existing simulation, raw JPEG/PNG upload, inference, dataset capture/training, zones, tracking/analytics, signal scenarios, network experiments and normalized decision evidence remain in place.

Physical/public-road traffic-signal control is outside scope.
