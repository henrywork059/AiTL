# AiTL V038 R9 camera architecture benchmark

This sketch is **diagnostic-only**. It does not replace the normal AiTL ESP32-CAM firmware and does not promote `0_3_8` or change the owner-confirmed `0_2_4` passed baseline.

## Purpose

R9 isolates whether the current low camera frame rate is mainly caused by the manual ESP socket writer, capture/send coupling, the camera/JPEG path, or a common ESP/network/AP/PC path.

The same one-click PC Studio Camera Diagnostics action compares:

1. manual `WiFiServer` / `WiFiClient` MJPEG;
2. older V035-style `esp_http_server` + `httpd_resp_send_chunk()` direct MJPEG;
3. Pi-style FreeRTOS newest-frame producer/cache + `esp_http_server` MJPEG;
4. camera-free `esp_http_server` 512 KiB bulk TCP;
5. camera-free raw `WiFiClient` bulk with `TCP_NODELAY` enabled;
6. camera-free raw `WiFiClient` bulk with Nagle enabled.

The sketch also reports framebuffer count/location/grab mode, HTTPD readiness, ESP reset reason including brownout reset evidence, RSSI/BSSID/channel and memory telemetry.

## Flash

1. Copy `secrets.example.h` to `secrets.h` in this folder.
2. Put the same 2.4 GHz Wi-Fi SSID/password used by the camera into `secrets.h`.
3. Open `AiTL_ESP32_CAM_ARCH_DIAG.ino` in Arduino IDE and upload it to the AI Thinker ESP32-CAM.
4. Confirm Serial Monitor prints `AiTL 0_3_8 R9 camera architecture benchmark`, `Camera ready: yes` and `HTTPD ready: yes`.
5. Keep the saved PC Studio camera profile pointed at the ESP's current private-LAN IP.
6. In PC Studio open **Camera Test -> Diagnose camera**.

The backend detects firmware beginning `aitl-0_3_8-r9-architecture-benchmark` and automatically selects the R9 engine.

## Main interpretations

- `manual_socket_sender_regression`: old-style HTTPD is fast while manual `WiFiClient` is much slower. Prefer HTTPD as the next production prototype.
- `capture_send_coupling`: the Pi-style latest-frame cache is much faster than direct HTTPD. Decouple capture from network sending and discard stale frames.
- `camera_or_jpeg_pipeline_specific`: camera-free TCP has strong throughput but all real-camera paths remain slow. Instrument framebuffer/JPEG memory handling.
- `common_network_or_esp_stack_bottleneck`: camera-free TCP itself is below 1 Mbit/s. Repeat on another AP/hotspot and a known-good 5 V supply before changing camera code.
- `httpd_architecture_healthy`: an HTTPD camera path reaches at least 70% of the diagnostic target. Treat it as the leading production prototype, not a passed release.
- `mixed_architecture_bottleneck`: current evidence does not isolate one layer.

A reported brownout reset is concrete power-path evidence. A non-brownout reset does **not** prove that the supply voltage never sagged.

## Ports

- `80`: control/status/config
- `84`: manual `WiFiClient` MJPEG
- `85`: `esp_http_server` direct/cached MJPEG and HTTPD bulk
- `87`: raw camera-free TCP bulk

The normal production managed camera worker is intentionally not tested while R9 firmware is flashed. After a transport architecture is selected, implement it in normal firmware and rerun the standard Camera Diagnostics workflow.
