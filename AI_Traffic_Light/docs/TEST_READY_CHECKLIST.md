# V0310 Acceptance Checklist

- [ ] `VERSION` is `0_3_10`; previous is `0_3_9`; passed baseline remains `0_2_4`.
- [ ] `docs/PATCH_0_3_10.md`, `CHANGELOG.md`, and the shared frontend `PROJECT_VERSION` all identify the same V0310 candidate.
- [ ] The normal Windows command remains reusable:

  ```powershell
  & "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
  ```

- [ ] The normal full workflow passes Python compile, structure validation, all automatic backend regressions, frontend typecheck/build, Git cleanliness and live backend smoke.
- [ ] `scripts/test_v0310_camera_pipeline.py` passes.
- [ ] PlatformIO builds `src/main_v0310.cpp` as the production entrypoint without separately compiling `src/main.cpp`.
- [ ] Arduino IDE production firmware exists at `apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino`.
- [ ] Serial Monitor shows the V0310 R10-tuned production marker after flashing.
- [ ] The PSRAM camera path uses exactly one framebuffer and `CAMERA_GRAB_LATEST`.
- [ ] The V0310 hot path uses plain non-blocking `send()` with at most 11,680 bytes per application write while retaining inherited progress/deadline/reconnect handling.
- [ ] `TCP_NODELAY`, keepalive, no-catch-up freshness scheduling, complete-frame semantics and deterministic failed-frame socket close remain intact.
- [ ] The PC wire format remains port 81 `aitl-tcp-jpeg-v1` with the 16-byte `ATL1` header; existing PC Studio receiver/session code remains compatible.
- [ ] Connect remains status/control only; Start applies the complete saved `/config`, activates `/start`, then opens the persistent stream; Stop ends the image session.
- [ ] Saved frame size, JPEG quality and target FPS remain authoritative. V0310 does not silently force diagnostic JPEG quality 18 or automatically degrade image quality/resolution.
- [ ] The Pi-style cache layer is not added to production; the separate R10 diagnostic sketch remains available for A/B comparison.
- [ ] At the previously tested good Wi-Fi position, a 15 FPS request is physically tested on the real Camera Sources production path using the existing saved image profile.
- [ ] A useful physical target is approximately 10–12 FPS sustained, complete JPEGs, no sustained send-deadline loop, no unexpected reconnect churn and unchanged configured image quality/resolution.
- [ ] Camera Sources preview, Live AI, Dataset Capture, zones and analytics continue to consume the selected physical source normally.
- [ ] Stop/Start and Disconnect/Connect are physically verified once after flashing V0310.
- [ ] Existing remote-camera/multi-camera, simulation, inference, dataset/training, analytics, signal logic and network-simulation regressions remain passing.
- [ ] V039 idempotent runner behavior remains intact and does not terminate unrelated processes on ports 8000/5173.
- [ ] No new stable API envelope/error code or physical/public-road traffic-control authority is introduced.
- [ ] The R10 diagnostic 12.43 FPS result is not relabeled as a V0310 production result unless the production ATL1 path actually measures it.
- [ ] Owner explicitly accepts V0310 before `passed_baseline` changes.
