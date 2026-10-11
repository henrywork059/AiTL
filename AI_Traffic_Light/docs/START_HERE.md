# Start Here — V0319

V0319 / `0_3_19` is the collapsible Camera Settings and saved-camera status candidate. Previous candidate: `0_3_18` (unaccepted). Owner-confirmed passed baseline: `0_3_11`.

## What changed

- Camera Settings now shows a color-coded status strip for **every saved camera**, including the selected preview and live connected/streaming/reconnecting/paused/unreachable states.
- The selected camera dropdown and Start/Stop controls remain visible. Expand **Manage IP addresses and connections** to add, save, connect, disconnect or delete devices; expand **Camera settings** to configure OV2640 settings/target FPS; expand **Detailed camera & stream status** for telemetry.
- Removed old version-specific streaming descriptions and the compatibility prose panel. The existing backend/firmware and one-selected-source AI pipeline are unchanged.

## Update and validate

```powershell
& "W:\\Code Project\\AiTL Ptoject\\AiTL\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```

A full Windows runner and real ESP check remain required for owner acceptance. `0_3_11` stays the accepted baseline until explicit PASS.
