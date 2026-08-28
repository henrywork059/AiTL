# V035 Acceptance Checklist

1. VERSION is `0_3_5`; previous `0_3_4`; baseline remains `0_2_4`.
2. Connect requests `/status` only and sends zero images.
3. Start applies full settings and target FPS before image transport.
4. PC uses one persistent MJPEG stream with TCP keepalive.
5. Multipart parser uses exact Content-Length and handles split network chunks.
6. Backlogged complete frames are discarded in favor of newest.
7. Physical browser preview wakes on frame notification rather than 10 ms polling.
8. Transport reports connected/reconnecting state separately.
9. ESP reboot/lost session automatically triggers status probe + config/start recovery.
10. Reconnect uses bounded exponential backoff rather than fixed rapid retry.
11. Stop closes the active socket promptly before ESP `/stop`.
12. Simulation suspends and later resumes physical transport.
13. ESP HTTPD TCP_NODELAY/keepalive/timeouts compile under the installed Arduino ESP32 core.
14. Full inherited backend regressions pass.
15. Frontend typecheck/build and live smoke pass.
16. Real ESP test shows equal-or-better latency and materially stronger recovery than V034.
17. Owner explicitly accepts V035 before `passed_baseline` changes.
