# V033 Acceptance Checklist

V033 is an unaccepted candidate. V024 / `0_2_4` remains the passed baseline.

1. VERSION/changelog/patch docs report V033 / `0_3_3`, previous V032, baseline V024.
2. Connect uses ESP `/status` only and causes no image request.
3. ESP `/capture` and `/stream` reject image access while idle.
4. Start sends every validated camera setting before ESP `/start`.
5. No PC `/capture` request occurs until `/start` succeeds.
6. PC-controlled resolution and JPEG quality are reflected in received frames/status.
7. Brightness/contrast/saturation and advanced OV2640 controls are sent/applied.
8. Stop ends the PC worker and disables the ESP session while retaining the connection.
9. Re-start can use different settings without reflashing the ESP.
10. Simulation pauses/resumes PC capture requests.
11. Legacy raw upload remains functional.
12. Dataset Capture and Live AI use the same physical-frame pipeline.
13. Private-LAN target validation remains intact and redirects remain disabled.
14. Python compile/focused regression/structure checks pass.
15. All inherited backend regressions pass.
16. Frontend typecheck/build pass.
17. Live smoke reports `0_3_3`.
18. Physical Arduino compile/upload and real-device session test pass.
19. No physical/public-road traffic-signal control claim/path is introduced.
20. Owner explicitly accepts V033 before `passed_baseline` changes.
