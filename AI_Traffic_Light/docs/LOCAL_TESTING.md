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

## Focused V037 checks

- V037 firmware keeps `sendmsg(..., MSG_DONTWAIT)` and the V036 `ATL1` frame format.
- V037 status reports configured/effective JPEG quality, adjustment count and send EWMA.
- failed/slow/large sends can only increase the effective JPEG quality number up to 50;
- sustained fast/small delivery can only recover toward, never below, the saved configured quality;
- `/config` resets adaptive quality to the newly saved configured value;
- PC accepts `aitl-camera-v037` and migration-compatible `aitl-camera-v036`, but rejects V035 HTTP/MJPEG firmware;
- new profiles default to QVGA / JPEG 24 / 15 FPS without rewriting existing saved profiles;
- multi-ESP switching, simulation pause/resume, Live AI and Dataset Capture remain intact.

## Physical test

1. Flash `AiTL_ESP32_CAM_V037.ino` and confirm `AiTL V037 R2 single-window adaptive-JPEG ESP32-CAM node`.
2. Use 320 × 240 / JPEG 24 / 15 FPS.
3. Run at least two minutes while moving objects through the frame.
4. Watch serial values: `fps`, `frame`, `send`, `q`, `ewma`, `adj`, `failures`, `rssi`.
5. A pressured link should raise `q` above the saved value, shrink JPEGs, then stabilize rather than continuously reconnect.
6. When the link remains fast, `q` should slowly return toward the saved configured value.
7. On PC Studio confirm frame age remains current, failure streak settles, reconnects do not climb continuously, and measured FPS improves over the V036 test under equivalent conditions.

Do not claim a speed improvement until this physical comparison is completed.

## V037 R2 single-window transport check

After Start Stream, the first few captured frames may be skipped locally while the ESP raises compression. This is expected and should not increment PC reconnects.

Healthy convergence should show:

```text
targetB=5000 (or a learned lower value)
localdrop=<small count that stops growing rapidly>
learn=0 or a small stable count
frame≈targetB or lower
accepted≈frame+16
errno=0
send normally well below the previous 100–500 ms range
failures stable
```

If `q` reaches 50 and frames remain much larger than `targetB`, reduce resolution rather than continuing to increase timeouts.


## V037 R4 physical check

After flashing R4, Serial Monitor must identify `AiTL V037 R4 adaptive-resolution ESP32-CAM node`. Start with 320 × 240 / JPEG 24 / 15 FPS. When a frame remains above `targetB` at maximum compression, verify `resdown` increments and `res=<actual>/<effective enum>` steps downward instead of sending the oversized frame. `localdrop` may rise during convergence. Once stable headroom persists, `resup` may increment slowly toward the saved resolution. The saved Camera Sources resolution must not be rewritten by runtime adaptation.
