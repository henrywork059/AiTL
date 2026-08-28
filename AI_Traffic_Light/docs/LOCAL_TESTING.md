# Local Testing — V035

Expected:

```text
version: 0_3_5
previous_version: 0_3_4
passed_baseline: 0_2_4
```

Run:

```powershell
.\scripts\update_test_run.ps1
```

Focused regressions must verify:
- private-LAN validation;
- old interval→FPS compatibility;
- Content-Length parsing across split TCP chunks;
- newest-frame backlog dropping;
- Connect transfers zero images;
- event-driven frame wait/wakeup;
- automatic lost-session recovery;
- simulation pause/resume;
- bounded Stop/Disconnect.

## Physical stability test

1. Flash only the updated V035 `.ino`; keep the existing `secrets.h`.
2. Connect: confirm ESP `session_active=false` and `stream_client_active=false`.
3. Start VGA / JPEG 12–16 / 15 FPS.
4. Confirm PC reports `stream_connected=true`.
5. Confirm measured FPS is stable and `stream_reconnects=0`.
6. Move an object quickly and compare visible delay with V034.
7. Temporarily power-cycle/reset the ESP while PC Studio still wants the stream.
8. After Wi-Fi returns, confirm `session_recoveries` increments and video resumes without manually pressing Start.
9. Test 20 FPS and retain it only if reconnect count/failure streak remain near zero.
10. Test simulation pause/resume, Live AI and Dataset Capture.
