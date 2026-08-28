# Start Here — Current V033 candidate

V033 / `0_3_3` is the current unaccepted candidate. V032 is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Main change

The ESP no longer starts transferring images simply because PC Studio connects.

V033 separates **connection** from **streaming**:

```text
Connect
  → status/control only
  → ESP stays idle

Start Stream
  → PC sends complete camera settings
  → ESP applies settings
  → ESP session starts
  → PC starts /capture requests

Stop Stream
  → PC stops requests
  → ESP session stops
  → device remains connected/idle
```

The ESP sends JPEG bytes only in response to image requests while the PC-started session is active.

## Settings owned by PC Studio

Resolution, JPEG quality, brightness, contrast, saturation, effects, white balance, exposure, gain, sensor corrections, mirror, flip, downsize/crop and color bar are supplied at Start Stream. The capture interval is a PC-side polling setting.

Use the matching `AiTL_ESP32CAM_V033_ArduinoIDE.zip` firmware.

Owner acceptance is still required before `passed_baseline` changes.
