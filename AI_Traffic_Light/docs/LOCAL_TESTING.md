# Local Testing — V038

Expected release state:

```text
version: 0_3_8
previous_version: 0_3_7
passed_baseline: 0_2_4
```

After the extracted V038 files are on GitHub `main`, use the normal updater:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
.\scripts\update_test_run.ps1
```

If the patch was deliberately overlaid directly onto the local working tree instead, use `-SkipUpdate`.

## Focused V038 checks

- Existing V037/R6 ESP firmware and `aitl-tcp-jpeg-v1` remain compatible; no ESP reflash is required for the diagnostics page.
- **Operate → Camera Test** appears as a separate page; `App.tsx` remains composition-only.
- With no saved/selected ESP, Diagnose is disabled and the page tells the user to configure Camera Sources first.
- With a selected ESP, one Diagnose action calls `POST /api/camera/diagnostics/run` and waits for the staged report.
- The service serializes diagnostic runs so two one-click tests cannot compete for the same camera.
- A run temporarily quiesces the selected stream and simulation when necessary, then restores saved settings/FPS and the previous connection/stream/simulation state.
- Control probes, protocol/camera readiness, Wi-Fi, direct stream, direct stream + status polling, and normal PC Studio managed-stream checks are all returned in the standard success envelope.
- A direct stream failure with increased ESP `stream_send_failures` / `stream_deadline_drops` classifies as `esp_camera_tcp_send_stall`.
- Direct streaming passing while the managed worker fails classifies as `pc_studio_stream_integration`.
- Direct streaming passing until status polling is added classifies as `control_stream_contention`.
- Weak RSSI with otherwise working transport is a warning rather than falsely blaming the camera sensor.
- The diagnostic report never claims public-road authority or production camera validation.

## Physical acceptance check

1. Keep the current V037/R6 firmware on the ESP and confirm its IP in Serial Monitor.
2. Save/select that IP in Camera Sources.
3. Open **Camera Test** and press **Diagnose camera** once.
4. Confirm the page completes without a command-line helper and displays a diagnosis, layer checks, transport metrics, and recommended action.
5. Confirm the previous camera stream/simulation state is restored after the run.
6. For the currently observed failure, verify the report distinguishes whether the direct camera/TCP path itself fails or whether failure appears only in the normal PC Studio worker.
