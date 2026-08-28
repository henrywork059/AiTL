# Local Testing — V036

Expected release state:

```text
version: 0_3_6
previous_version: 0_3_5
passed_baseline: 0_2_4
```

Run the normal repository test workflow:

```powershell
.\scripts\update_test_run.ps1
```

Focused regressions must verify:

- literal private-LAN ESP IPv4 validation;
- V035/mismatched firmware rejected during Connect;
- fixed 16-byte frame header survives arbitrary TCP segmentation;
- invalid magic/length/incomplete JPEG is rejected;
- old interval→FPS API compatibility;
- Connect transfers zero images;
- Start order remains `/stop → /config → /start → TCP`;
- event-driven browser frame wakeup;
- automatic lost-session recovery;
- simulation pause/resume;
- bounded Stop/Disconnect.

## Physical speed/latency test

1. Flash the matching V036 firmware.
2. On Serial Monitor, record the ESP IP.
3. In PC Studio enter that ESP IP and Connect.
4. Confirm `/status` reports `protocol=aitl-camera-v036`, `stream_protocol=aitl-tcp-jpeg-v1`, `session_active=false` and no stream client.
5. Start at VGA / JPEG 14 / 15 FPS.
6. Confirm PC reports `transport=tcp_jpeg` and `stream_connected=true`.
7. Confirm ESP `last_frame_bytes > 0`, `stream_frame_count` rises, `actual_fps` is stable, and recurring `cam_hal: FB-OVF` is absent.
8. Move a high-contrast object rapidly across the frame. Compare visible delay and motion smoothness with V035 if available.
9. Run at least two minutes. Prefer `stream_reconnects=0` under normal Wi-Fi; occasional reconnects under forced congestion are acceptable if video resumes fresh rather than replaying old frames.
10. Reset/power-cycle the ESP while PC Studio still wants the stream. Confirm `session_recoveries` increments and video returns without pressing Start again.
11. Test 20 FPS. Retain it only if actual FPS approaches target without rising send failures/reconnects.
12. Test simulation pause/resume, Live AI and Dataset Capture.

## Diagnose speed limits

If measured FPS is low, compare ESP telemetry:

- high `last_capture_ms`: camera/resolution/quality is the bottleneck;
- high `last_send_ms` or `stream_deadline_drops`: Wi-Fi/network is the bottleneck;
- rising `source_sequence_gaps`: frames were lost across a transport/reconnect interval;
- recurring `FB-OVF`: investigate camera/PSRAM/power before increasing FPS.
