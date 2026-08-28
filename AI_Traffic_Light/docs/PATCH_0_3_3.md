# Patch 0_3_3 — PC-controlled on-demand ESP camera session

## Release state

- Candidate: V033 / `0_3_3`
- Previous candidate: V032 / `0_3_2`
- Passed baseline: V024 / `0_2_4`

## Goal

Keep the ESP camera idle until PC Studio explicitly starts a session, and make PC Studio the authority for runtime OV2640 camera settings.

## PC workflow

1. **Connect** — probe `/status`; no image request.
2. Edit camera settings.
3. **Start Stream**:
   - send full settings to ESP `POST /config`;
   - call `POST /start`;
   - start bounded PC `/capture` polling.
4. **Stop Stream**:
   - stop PC polling;
   - call `POST /stop`;
   - ESP returns to idle.
5. **Disconnect** — stop best-effort then clear the PC device connection.

## Same-candidate regression repair

The first V033 candidate retained the V032 `scripts/test_remote_camera_pull.py`. That old regression expected `connect(..., fetch_interval_ms=100)` to start the image worker immediately. V033 intentionally removed both behaviors.

The repaired regression now verifies the V033 contract:

- Connect performs `/status` only and requests zero images.
- Start Stream performs `/stop` → `/config` → `/start` before image polling.
- Active sessions feed the existing `CameraFrameService`.
- Simulation pauses/resumes PC image requests.
- Stop Stream stops the worker while keeping the ESP connection.
- Disconnect/shutdown remains safe.

This is a **same-candidate V033 test repair**, not V034. Runtime implementation, API, firmware, `VERSION`, and `passed_baseline` are unchanged.

## PC-controlled settings

V033 retains PC-owned resolution, JPEG quality, image adjustment, white-balance, exposure, gain, correction, mirror/flip/downsize/color-bar settings and PC capture interval.

## Deliberate non-changes

- legacy raw device POST receiver remains;
- simulation remains;
- inference/training/analytics/signal/network logic remains PC-side;
- no persistent PC remote-camera configuration yet;
- no independent simultaneous multi-camera frame store yet;
- no public-road traffic control.
