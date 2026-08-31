# AiTL V038 R10 camera tuning benchmark

This sketch is **diagnostic-only**. It does not replace the normal AiTL ESP32-CAM firmware and does not promote `0_3_8` or change the owner-confirmed `0_2_4` passed baseline.

## Purpose

R10 extends the R9 architecture benchmark into a controlled tuning matrix. It measures which framebuffer/grab-mode combination, target FPS, newest-frame architecture, JPEG payload and TCP application write size give the best fresh-frame performance on the same ESP/network.

The same one-click PC Studio **Camera Test -> Diagnose camera** action now runs:

1. framebuffer/grab-mode matrix:
   - `fb_count=1`, `CAMERA_GRAB_WHEN_EMPTY`;
   - `fb_count=1`, `CAMERA_GRAB_LATEST`;
   - `fb_count=2`, `CAMERA_GRAB_WHEN_EMPTY`;
   - `fb_count=2`, `CAMERA_GRAB_LATEST`;
2. each framebuffer mode at 3, 5, 10 and 15 FPS targets;
3. the winning framebuffer mode with the Pi-style newest-frame producer/cache at 3, 5, 10 and 15 FPS;
4. JPEG quality/payload trade-off at quality values 18, 24, 30 and 36 plus the currently configured quality;
5. camera-free raw TCP write-size sweep at 1460, 2920, 5840 and 11680 bytes;
6. camera-free transfer-size sweep at 32 KiB, 128 KiB and 512 KiB using the best write size;
7. three repeat bulk runs to expose RF/AP/network variability;
8. exact restoration of the original framebuffer, grab mode, frame size and JPEG quality.

R10 retains the R9 controls and telemetry: `esp_http_server`, Pi-style cached MJPEG, camera-free TCP, `TCP_NODELAY`, reset reason/brownout evidence, RSSI/BSSID/channel and memory telemetry.

## Flash

1. Copy `secrets.example.h` to `secrets.h` in this folder.
2. Put the same 2.4 GHz Wi-Fi SSID/password used by the camera into `secrets.h`.
3. Open `AiTL_ESP32_CAM_ARCH_DIAG.ino` in Arduino IDE and upload it to the AI Thinker ESP32-CAM.
4. Confirm Serial Monitor prints `AiTL 0_3_8 R10 camera tuning benchmark`, `Camera ready: yes` and `HTTPD ready: yes`.
5. Keep the saved PC Studio camera profile pointed at the ESP's current private-LAN IP.
6. In PC Studio open **Camera Test -> Diagnose camera**.

The firmware intentionally preserves the R9 family marker `aitl-0_3_8-r9-architecture-benchmark` for compatibility and adds `tuning_revision: R10` in `/status`. The backend checks the R10 revision first, so R10 runs the tuning service while older R9 firmware still runs the architecture-only service.

## Main interpretations

- `network_limited_after_tuning`: even the best camera-free raw TCP control remains below 1 Mbit/s. RF/AP placement, ESP Wi-Fi/lwIP, PC receive path or power/network conditions remain the first limiter.
- `framebuffer_configuration_sensitive`: a non-default FB/grab combination materially improves sustainable target FPS. Prototype that combination in normal firmware.
- `capture_send_coupling`: newest-frame producer/cache materially beats direct capture/send. Decouple capture from transmission and skip stale frames.
- `tcp_write_batching_sensitive`: larger/smaller application writes materially outperform 1460-byte writes. Prototype the winning write size in the production sender.
- `tuning_profile_identified`: no single abnormal bottleneck dominates; use the measured recommended profile for the next production prototype.

The report also identifies:

- best sustainable target FPS using a 70% target-attainment threshold;
- best framebuffer/grab mode;
- direct versus cached newest-frame architecture;
- highest JPEG quality that still clears the tested performance threshold;
- best raw TCP application write size;
- fixed connection/startup overhead from transfer-size scaling;
- run-to-run RF/AP/network variability.

A reported brownout reset is concrete power-path evidence. A non-brownout reset does **not** prove that the supply voltage never sagged.

## Ports

- `80`: control/status/config and `/camera/reinit`
- `84`: manual `WiFiClient` MJPEG control path retained from R9
- `85`: `esp_http_server` direct/cached MJPEG and HTTPD bulk
- `87`: raw camera-free TCP bulk with configurable write size

The normal production managed camera worker is intentionally not tested while this diagnostic firmware is flashed. After a tuning profile is selected, implement it in normal firmware and rerun the standard Camera Diagnostics workflow before considering the transport change accepted.
