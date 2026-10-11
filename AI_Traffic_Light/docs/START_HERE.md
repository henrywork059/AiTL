# Start Here — V0318

V0318 / `0_3_18` is the Camera Settings page candidate. Previous candidate: `0_3_17` (unaccepted). Owner-confirmed passed baseline: `0_3_11`.

## What changed

- Open **Camera Settings** from the Operate sidebar to add ESP32-CAM devices by IP, select the active feed from a saved-camera dropdown, inspect live preview/connection/FPS and device diagnostics, and configure per-camera image settings and target streaming FPS.
- **Camera Sources** now focuses on frame input and simulation controls. Existing camera persistence, transport and one-selected-source AI pipeline remain unchanged.
- To apply settings to a running camera, stop its stream, edit/save settings, then reconnect/start it; camera controls remain locked during streaming.

## Update and validate

```powershell
& "W:\\Code Project\\AiTL Ptoject\\AiTL\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```

Complete owner acceptance still requires full validation and a physical ESP camera check. No ESP reflash or backend API change is required. `0_3_11` remains the accepted baseline until explicit owner PASS.
