# V036 Acceptance Checklist

1. `VERSION` is `0_3_6`; previous candidate `0_3_5`; passed baseline remains `0_2_4`.
2. Matching V036 PlatformIO firmware and standalone Arduino IDE sketch compile for AI Thinker ESP32-CAM.
3. ESP requires Wi-Fi credentials only; no PC/server IP is required in firmware.
4. Connect requests `/status` only and transfers zero image bytes.
5. V035/mismatched firmware produces a clear compatibility error during Connect.
6. Start applies full OV2640 settings and target FPS before opening image transport.
7. ESP→PC image transport is one persistent length-prefixed TCP JPEG connection on port 81.
8. Fixed header is `ATL1 + length + sequence + source uptime`; split TCP segments are handled correctly.
9. PC validates payload length and JPEG boundaries.
10. ESP uses JPEG, two PSRAM framebuffers and `CAMERA_GRAB_LATEST` when PSRAM exists.
11. ESP allocation starts at UXGA before applying the selected runtime frame size.
12. ESP/PC stream sockets use `TCP_NODELAY`; keepalive remains enabled.
13. Frame cadence does not add a post-send delay on top of the target period.
14. A congested ESP send is abandoned by deadline rather than queued for seconds.
15. PC stream stall timeout/reconnect is bounded and automatic session restoration still works.
16. Browser preview remains event-driven and uses the shared PC frame service.
17. Simulation suspends and later resumes the physical stream.
18. Live AI and Dataset Capture still consume physical frames correctly.
19. Focused backend tests, full inherited backend regressions, structure checks and smoke pass on the complete repository.
20. Frontend typecheck/build passes.
21. Physical VGA/JPEG14/15 FPS test shows stable streaming with no recurring framebuffer overflow.
22. Physical latency is equal to or lower than V035 and severe Wi-Fi congestion recovers to a fresh frame rather than visibly replaying backlog.
23. Owner explicitly accepts V036 before `passed_baseline` changes.
