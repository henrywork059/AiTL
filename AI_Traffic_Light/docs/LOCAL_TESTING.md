# Local Testing — V036

Expected release state:

```text
version: 0_3_6
previous_version: 0_3_5
passed_baseline: 0_2_4
```

After extracting the full V036 overlay, finalize the preserved changelog/version metadata once, then run the normal repository test workflow:

```powershell
.\scripts\apply_v036_full_patch.ps1
.\scripts\update_test_run.ps1 -SkipUpdate
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
- bounded Stop/Disconnect;
- persisted multi-camera IP/FPS/settings registry;
- two independent ESP streams active at once;
- non-selected streams cannot overwrite the selected `CameraFrameService` source;
- switching to another running ESP uses only a recent cached/latest frame and clears the former source when the target cache is stale;
- changing a selected profile IP invalidates cached bytes from the former device;
- stopping/disconnecting one ESP does not stop the others;
- backend shutdown disconnects every ESP session.

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


## Multi-camera physical test

1. Flash the same V036 firmware to two or more ESP32-CAM boards.
2. In Camera Sources choose **New camera**, enter the first private IPv4/source ID, set VGA / JPEG 14 / 15 FPS, then Save, Connect and Start Stream.
3. Add the second ESP with a different source ID/IP and Start Stream. Confirm the first ESP remains listed as streaming in the background.
4. Switch the Saved ESP camera selector between them. The preview, `active_source_id`, Live AI and Dataset Capture source must follow the selected ESP only.
5. Stop or disconnect one camera and confirm the other keeps streaming.
6. Restart PC Studio. Confirm both IPs and each camera's FPS/OV2640 settings are restored, while connection state correctly returns to disconnected until Connect is pressed.

### ESP send-stall diagnostic

For VGA/QVGA/HQVGA on a healthy local Wi-Fi link, repeated serial telemetry such as `send=300ms`, `send=700ms`, or `send=1100ms` together with rapidly increasing `failures`/PC reconnect counts indicates the stream socket is stalling and is not acceptable 15 FPS behavior. After the V036 same-candidate non-blocking send repair, reflash the ESP and verify `last_send_ms` is normally small, reconnect/failure counts remain stable, and PC measured FPS approaches the configured target. Do not diagnose this pattern as weak signal solely from RSSI when RSSI is around -55 to -65 dBm.

### V036 R6 ESP transport check

After flashing R6, confirm Serial Monitor identifies `AiTL V036 R6 warmup-vectored ESP32-CAM node`. During the first three successful frames of each TCP connection, `warmup=yes` is expected. A healthy connection should then stay connected with `errno=0`, accepted bytes approximately `frame + 16`, and failure/reconnect counters not climbing continuously.
