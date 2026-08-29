# V037 Acceptance Checklist

- [ ] `VERSION` is `0_3_7`; previous is `0_3_6`; passed baseline remains `0_2_4`.
- [ ] PlatformIO and standalone Arduino V037 firmware compile for AI Thinker ESP32-CAM.
- [ ] Connect remains status-only with zero image bytes.
- [ ] V037 keeps `aitl-tcp-jpeg-v1` and the 16-byte `ATL1` header.
- [ ] V037 firmware reports `aitl-camera-v037`; PC accepts V037 and V036 binary-TCP nodes during migration.
- [ ] New camera defaults are QVGA / JPEG 24 / 15 FPS; existing saved profiles are preserved.
- [ ] Adaptive quality never improves past the user's configured quality floor or exceeds the quality-number cap of 40.
- [ ] Slow/large/failed sends increase compression; sustained fast/small sends recover gradually.
- [ ] Status exposes configured/effective quality, adjustment count, send EWMA and existing send diagnostics.
- [ ] Multi-ESP profiles, simultaneous background streams, selected-source isolation and source-switch freshness guards still pass.
- [ ] Simulation pause/resume, browser preview, Live AI and Dataset Capture still work.
- [ ] Python compile, structure check, focused/inherited regressions, frontend typecheck/build and live smoke pass on the complete repository.
- [ ] Physical QVGA/JPEG24/15 FPS test runs for at least two minutes without continuously increasing reconnect/failure counts.
- [ ] Physical measured FPS/send latency is materially better than the owner's V036 R6 observation under comparable Wi-Fi conditions.
- [ ] Owner explicitly accepts V037 before `passed_baseline` changes.

- [ ] V037 R2 skips oversized frames locally while adaptive compression can still increase, rather than sending a known-oversize ATL1 record and forcing a reconnect.
- [ ] `adaptive_payload_target_bytes` starts at 5000 B and can learn a lower safe target from a partial TCP send.
- [ ] After initial convergence, `adaptive_local_frame_drops` does not increase continuously during a stable scene.
- [ ] Successful `accepted` bytes equal JPEG bytes + 16-byte ATL1 header and `errno=0`.
- [ ] Camera Sources displays payload target, oversize local-drop count and TCP-window learn count.


- [ ] R4: at maximum JPEG compression, a frame above `adaptive_payload_target_bytes` is not sent merely because the quality ceiling was reached.
- [ ] R4: effective resolution may downshift under sustained oversize pressure while saved/configured resolution remains unchanged.
- [ ] R4: sustained headroom recovers effective resolution before JPEG quality recovery; Serial/Camera Sources expose down/up counts and effective size.
