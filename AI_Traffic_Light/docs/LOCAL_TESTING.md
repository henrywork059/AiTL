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

## Focused V037 checks

- V037 firmware keeps `sendmsg(..., MSG_DONTWAIT)` and the V036 `ATL1` frame format.
- V037 status reports configured/effective JPEG quality, adjustment count and send EWMA.
- failed/slow/large sends can only increase the effective JPEG quality number up to 40;
- sustained fast/small delivery can only recover toward, never below, the saved configured quality;
- `/config` resets adaptive quality to the newly saved configured value;
- PC accepts `aitl-camera-v037` and migration-compatible `aitl-camera-v036`, but rejects V035 HTTP/MJPEG firmware;
- new profiles default to QVGA / JPEG 24 / 15 FPS without rewriting existing saved profiles;
- multi-ESP switching, simulation pause/resume, Live AI and Dataset Capture remain intact.

## Physical test

1. Flash `AiTL_ESP32_CAM_V037.ino` and confirm `AiTL V037 adaptive-JPEG ESP32-CAM node`.
2. Use 320 × 240 / JPEG 24 / 15 FPS.
3. Run at least two minutes while moving objects through the frame.
4. Watch serial values: `fps`, `frame`, `send`, `q`, `ewma`, `adj`, `failures`, `rssi`.
5. A pressured link should raise `q` above the saved value, shrink JPEGs, then stabilize rather than continuously reconnect.
6. When the link remains fast, `q` should slowly return toward the saved configured value.
7. On PC Studio confirm frame age remains current, failure streak settles, reconnects do not climb continuously, and measured FPS improves over the V036 test under equivalent conditions.

Do not claim a speed improvement until this physical comparison is completed.
