# V034 Acceptance Checklist

1. VERSION is `0_3_4`; previous is `0_3_3`; passed baseline remains `0_2_4`.
2. Connect transfers zero images.
3. Start applies all OV2640 settings plus target FPS before opening MJPEG.
4. One persistent ESP stream replaces repeated per-frame `/capture` requests.
5. JPEG parsing handles network chunk boundaries.
6. CameraFrameService receives continuous frames.
7. Measured FPS/interval/reconnect/byte telemetry updates.
8. Camera Sources uses backend `/api/camera/live.mjpeg`.
9. Stop closes the active stream promptly.
10. Simulation pauses and later reopens physical image transport.
11. V033 `fetch_interval_ms` callers remain compatible.
12. Private-LAN/redirect protections remain.
13. Full inherited regressions/typecheck/build/live smoke pass.
14. Real ESP test shows smoother motion/lower delay than V033 at comparable image settings.
15. No public-road control claim/path is introduced.
16. Owner explicitly accepts V034 before `passed_baseline` changes.
