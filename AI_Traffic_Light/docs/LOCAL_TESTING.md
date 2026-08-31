# Local Testing — V0310

Expected release state:

```text
version: 0_3_10
previous_version: 0_3_9
passed_baseline: 0_2_4
```

## Normal update / test / run

Use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The helper should fast-forward `main`, reload itself, refresh dependencies, run Python compile/structure/regressions, frontend typecheck/build, Git cleanliness and live backend smoke, safely replace an existing AiTL-owned PC Studio instance on ports 8000/5173, and relaunch the app. Unrelated port owners remain protected.

## Focused V0310 offline checks

- `scripts/test_v0310_camera_pipeline.py` passes.
- PlatformIO selects `src/main_v0310.cpp` rather than compiling legacy `src/main.cpp` separately.
- V0310 keeps the existing `ATL1` / `aitl-tcp-jpeg-v1` PC wire contract.
- The PSRAM path uses one framebuffer + `CAMERA_GRAB_LATEST`.
- The production sender uses plain non-blocking `send()` underneath the inherited progress/deadline loop with an 11,680-byte maximum application write.
- Saved frame size/JPEG quality/FPS remain PC-controlled; no diagnostic q18 override or automatic image-quality degradation is introduced.
- The R10 architecture diagnostic sketch remains separate and available.
- Existing remote-camera/session/multi-camera, simulation, inference, dataset, analytics and signal/network regressions remain passing.

## Arduino IDE physical test

1. Pull V0310 with the normal command and allow the full regression/build/smoke run to pass.
2. In `apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/`, copy `secrets.example.h` to `secrets.h` if needed and enter the same 2.4 GHz Wi-Fi credentials used for the working diagnostic.
3. Open `AiTL_ESP32_CAM_V0310.ino` in Arduino IDE and upload with the same board/port settings used previously.
4. Open Serial Monitor at 115200 and confirm `AiTL V0310 R10-tuned production pipeline active` plus the ESP IP.
5. Keep the ESP in the previously tested good Wi-Fi position.
6. In PC Studio Camera Sources, save/select the current ESP IP, Connect, and Start Stream.
7. Use the existing saved image settings. Request 15 FPS for the main comparison; do not change JPEG quality solely to manufacture a higher FPS result.
8. Observe production measured FPS, `send_ewma_ms`, send failures/deadlines, RSSI/BSSID/channel and reconnect behavior for a sustained run.
9. Verify Camera Sources preview, Live AI, Dataset Capture, zones and analytics receive complete current frames.
10. Stop/Start once and Disconnect/Connect once to verify the inherited lifecycle and recovery behavior.

## Acceptance interpretation

A useful target at the good Wi-Fi position is approximately 10–12 FPS sustained on the **production ATL1 path**, with complete JPEGs, no sustained deadline-failure loop, no unexpected reconnect churn and unchanged configured image quality/resolution.

The R10 diagnostic's 12.43 FPS at a 15 FPS target is comparative evidence for V0310 tuning, not an automatic production result. If V0310 production ATL1 remains materially below the R10 camera ladder, compare the ATL1 framing/PC receiver path directly against R10 HTTPD before adding cache/framebuffer complexity.

V024 / `0_2_4` remains the passed baseline until explicit owner acceptance. Physical/public-road traffic-control authority remains out of scope.
