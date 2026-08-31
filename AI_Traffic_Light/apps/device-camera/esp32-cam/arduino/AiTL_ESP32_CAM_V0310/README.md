# AiTL ESP32-CAM V0310 production firmware

Use `AiTL_ESP32_CAM_V0310.ino` for the V0310 physical production-camera test.

V0310 is based on the R10 physical tuning result and keeps the existing PC Studio `aitl-camera-v037` / `aitl-tcp-jpeg-v1` / `ATL1` compatibility contract. It changes the ESP hot path only:

- one framebuffer;
- `CAMERA_GRAB_LATEST` when PSRAM is available;
- plain non-blocking `send()` underneath the inherited progress/deadline sender;
- at most 11,680 bytes per application write;
- no Pi-style cache layer;
- no automatic JPEG-quality or resolution degradation.

Saved Camera Sources settings still control frame size, JPEG quality and target FPS through `/config`.

## Arduino IDE

1. Keep this folder inside the full pulled AiTL repository. The V0310 sketch intentionally includes the adjacent V037 implementation to avoid duplicating the mature control/session code.
2. Copy `secrets.example.h` to `secrets.h` in this V0310 folder and enter the 2.4 GHz Wi-Fi credentials.
3. Open `AiTL_ESP32_CAM_V0310.ino` in Arduino IDE.
4. Select the same AI Thinker ESP32-CAM board/port settings used for the prior working firmware.
5. Compile and upload, then open Serial Monitor at 115200 baud.
6. Confirm the serial marker contains `AiTL V0310 R10-tuned production pipeline active`.
7. In PC Studio, use Camera Sources → Connect → Start Stream with the saved profile.

The dedicated `AiTL_ESP32_CAM_ARCH_DIAG` sketch remains the R10 benchmark firmware and is not the production firmware.
