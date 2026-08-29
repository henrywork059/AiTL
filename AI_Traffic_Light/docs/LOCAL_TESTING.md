# Local Testing — V037

Expected release state:

```text
version: 0_3_7
previous_version: 0_3_6
passed_baseline: 0_2_4
```

After the extracted V037 files are on GitHub `main`, use the normal updater:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
.\scripts\update_test_run.ps1
```

If the patch was overlaid directly onto the local working tree instead, use `-SkipUpdate`.


## Normal updater worktree behavior

V037 R3 makes the runner read-only for tracked project/release files. A normal successful run must not leave `CHANGELOG.md`, `projectVersion.ts`, or any other tracked source modified. The updater still refuses to pull across genuine tracked edits and still preserves untracked runtime data.

If upgrading a PC that was previously dirtied by the historical V036 finalizer, restore only those already-generated metadata edits once before pulling R3. After R3 is installed, this cleanup should not recur.

## Focused V037 R6 checks

- Firmware keeps `sendmsg(..., MSG_DONTWAIT)`, TCP_NODELAY/keepalive and the V036-compatible `ATL1` frame format.
- PSRAM camera configuration uses exactly one framebuffer with `CAMERA_GRAB_WHEN_EMPTY`; XCLK remains 20 MHz.
- R2/R4 payload-target, partial-window learning, q=50 escalation and effective-resolution downshift code is absent.
- `/config` applies the saved JPEG quality and frame size directly; effective quality/size mirror the saved settings.
- A failed partial frame closes the client socket but does not modify JPEG quality or resolution.
- Status exposes `quality_preserving_transport`, send EWMA/slow-frame count, RSSI, BSSID, channel and ESP Wi-Fi disconnect/reconnect counts.
- PC accepts `aitl-camera-v037` and migration-compatible `aitl-camera-v036`; the wire format remains `aitl-tcp-jpeg-v1`.
- Multi-ESP switching, simulation pause/resume, Live AI and Dataset Capture remain intact.

## Physical R6 check

1. Flash `AiTL_ESP32_CAM_V037.ino` and confirm `AiTL V037 R6 quality-preserving TCP ESP32-CAM node`.
2. Start with 320 × 240 / JPEG quality 24 / 5–15 FPS.
3. Confirm Serial Monitor reports `fixed=yes`, `q=<saved>/<saved>`, RSSI, BSSID and channel.
4. Confirm image quality does not automatically collapse after a slow send: there must be no q=50 escalation and no runtime resolution downshift.
5. Under healthy Wi-Fi, `client=on` should remain stable and `failures`/`deadlines` should not climb continuously.
6. If the network slows, achieved FPS may fall below target. That is expected; freshness is preferred over queueing old frames.
7. If a send actually fails, the ESP closes that partial-frame socket and PC Studio should enter reconnecting then return to TCP JPEG connected without changing the saved image settings.
8. Compare the displayed BSSID/RSSI with the earlier strong and weak mesh/AP associations when diagnosing a recurrence.

The R6 acceptance criterion is stability **without image-quality self-degradation**, not forcing every requested FPS regardless of available Wi-Fi throughput.
