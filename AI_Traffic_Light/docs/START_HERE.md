# Start Here — V0310

V0310 / `0_3_10` is the current unaccepted candidate. V039 / `0_3_9` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Normal Windows workflow

For routine update, validation and launch, use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The V039 idempotent restart behavior remains: the helper may stop listeners on 8000/5173 only when Win32 process evidence identifies them as this repository's AiTL PC Studio process tree. Unrelated listeners are protected. Runtime/user data is preserved.

## V0310 production camera transport

V0310 applies the R10 physical tuning result to the real ESP camera path while deliberately keeping the PC Studio protocol unchanged:

```text
PC Connect -> ESP /status only
PC Start -> /config -> /start -> persistent TCP :81
ESP camera -> FB1 / CAMERA_GRAB_LATEST on PSRAM
ATL1 header + configured JPEG -> bounded plain send() writes, max 11680 B/write
selected ESP -> CameraFrameService -> preview / Live AI / capture / zones / analytics
```

The wire contract remains `aitl-camera-v037` compatible and `aitl-tcp-jpeg-v1`, so the existing PC receiver and saved multi-camera profiles continue to work. V0310's serial startup marker identifies the tuned production firmware.

Saved Camera Sources frame size, JPEG quality and target FPS remain authoritative. V0310 does **not** silently force R10's diagnostic JPEG-quality recommendation and does not reintroduce automatic quality/resolution degradation.

The Pi-style newest-frame cache is not added because the strong-Wi-Fi R10 run showed no matched-target throughput gain. Freshness is instead maintained by `CAMERA_GRAB_LATEST`, no catch-up backlog and the existing complete-frame/reconnect policy.

## Firmware to flash

For the production V0310 test, flash:

```text
apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino
```

The separate `AiTL_ESP32_CAM_ARCH_DIAG` sketch remains the R10 diagnostic benchmark and should only be used when re-running the framebuffer/FPS/network matrix.

## Physical target

At the same good Wi-Fi position used for the successful R10 run, request 15 FPS with the existing saved image settings. V0310 should now be tested on the **actual Camera Sources production path**. A useful acceptance target is a stable approximately 10–12 FPS with complete JPEGs, no sustained send-deadline loop, no unexpected reconnect churn, and unchanged configured image quality/resolution.

The earlier 12.43 FPS value belongs to the diagnostic R10 path and is not claimed for production until this V0310 firmware is physically verified.

AiTL remains a local/student-scale prototype; physical/public-road traffic-signal authority is out of scope.
