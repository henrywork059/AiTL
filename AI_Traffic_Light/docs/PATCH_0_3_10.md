# Patch 0_3_10 — R10-tuned production camera pipeline

V0310 / `0_3_10` is the current unaccepted candidate after V039. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Why V0310 exists

R10 physical Camera Diagnostics isolated framebuffer mode, target FPS, newest-frame caching, JPEG quality, TCP write size, transfer size and repeatability. In the strong-Wi-Fi run, the ESP reached 12.43 FPS at a 15 FPS target with one framebuffer + `CAMERA_GRAB_LATEST`; the Pi-style newest-frame cache did not improve the matched FPS ladder, and the camera-free raw TCP sweep improved materially as application writes increased to 11,680 bytes.

V0310 moves those supported findings into the actual production ESP camera path without changing the PC Studio wire/API contract.

## Implemented

- Added a V0310 production entrypoint for PlatformIO and a matching Arduino IDE sketch.
- PSRAM camera initialization still uses exactly one framebuffer but now selects `CAMERA_GRAB_LATEST` rather than the older `CAMERA_GRAB_WHEN_EMPTY` production choice.
- The inherited progress/deadline/reconnect sender remains non-blocking and freshness-first, but its real `sendmsg()` call is replaced by plain `send()` operations capped at 11,680 bytes per application write.
- TCP segmentation remains owned by lwIP/TCP; 11,680 bytes is an application write ceiling, not an MTU/MSS assumption.
- `TCP_NODELAY`, keepalive, bounded no-progress/total-send limits, deterministic partial-frame socket close, PC reconnect/session recovery and no-catch-up scheduling are retained.
- The PC transport remains port 81 `aitl-tcp-jpeg-v1`: 16-byte `ATL1` header followed by the complete JPEG payload. The production PC receiver remains unchanged.
- Connect remains status/control only; Start remains complete `/config` → `/start` → persistent TCP stream; Stop closes the image session.
- Saved Camera Sources frame size, JPEG quality and target FPS remain authoritative. V0310 does not silently force diagnostic JPEG quality 18 and does not reintroduce adaptive quality/resolution degradation.
- The Pi-style FreeRTOS newest-frame cache is not added to production because R10 measured no matched-target throughput benefit in the strong-Wi-Fi run.
- The separate R10 architecture/tuning diagnostic firmware remains available for A/B verification.

## Deliberate compatibility choice

V0310 retains the mature V037-compatible device/protocol identity on the HTTP/TCP contract so the existing PC Studio receiver, saved profiles and multi-camera session manager do not require a simultaneous migration. The V0310 firmware emits an explicit serial startup marker identifying the tuned production entrypoint.

This is intentional: V0310 tests whether the R10 capture/write improvements transfer to the production ATL1 pipeline before considering a later transport-protocol change.

## Physical evidence target

The R10 diagnostic result is evidence for the tuning choices, not proof that the production ATL1 path will automatically match the diagnostic HTTPD result. Physical acceptance therefore requires reflashing V0310 and measuring the actual production stream.

At the previously tested strong-Wi-Fi position, use the existing saved image profile and request 15 FPS. A useful V0310 acceptance target is a stable approximately 10–12 FPS production stream with:

- complete JPEG frames only;
- no sustained send-deadline failure loop;
- no unexpected disconnect/reconnect churn;
- image quality/resolution remaining exactly as configured;
- Camera Sources / Live AI / capture / zones / analytics continuing to consume the selected source normally.

If production ATL1 remains materially below the R10 diagnostic camera ladder after this patch, the next investigation should compare the ATL1 framing/PC receiver path directly against the R10 HTTPD path rather than adding more framebuffer/cache complexity.

## Acceptance procedure

1. Run the normal one-command PC Studio update/test/run workflow and confirm all offline regressions/build/smoke checks pass.
2. Flash `apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino`.
3. Confirm Serial Monitor at 115200 shows the V0310 tuned-production marker and the current ESP IP.
4. In Camera Sources, save/select the ESP IP, Connect, and Start Stream using the existing saved settings.
5. At the good Wi-Fi position, request 15 FPS and observe production measured FPS, send EWMA, send failures/deadlines, RSSI and reconnect behavior for a sustained run.
6. Verify Camera Sources preview, Live AI, capture, zones and analytics still receive complete current frames.
7. Stop/start and disconnect/reconnect once to verify the existing session recovery path.
8. Do not change `passed_baseline` until the owner explicitly accepts V0310.

AiTL remains a local/student-scale prototype. No physical/public-road traffic-signal authority is introduced.
