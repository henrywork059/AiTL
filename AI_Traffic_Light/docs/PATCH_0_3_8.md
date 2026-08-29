# Patch 0_3_8 — One-click camera diagnostics

V038 / `0_3_8` is a new candidate explicitly requested by the owner after V037. `passed_baseline` remains `0_2_4`.

## Why V038 exists

Physical V037/R6/R7 testing showed that camera failures can occur at different layers and that command-line isolation tests are too cumbersome for normal use. V038 makes that diagnostic workflow part of PC Studio.

## Implemented

- New **Operate → Camera Test / Camera Diagnostics** page.
- One **Diagnose camera** button against the currently selected saved ESP profile.
- Backend `CameraDiagnosticService` owns staged network/transport diagnosis; the HTTP route stays thin.
- Direct repeated `/status` reachability/latency probes.
- Firmware/wire-protocol and `camera_ready` validation.
- RSSI/BSSID/channel evidence.
- Direct ATL1/JPEG receiving that bypasses the normal PC Studio stream worker.
- A second direct-stream phase with concurrent `/status` polling to expose ESP control/data-plane contention.
- A separate normal `RemoteCameraManager`/`RemoteCameraService` stream phase to isolate PC Studio integration faults.
- Classification of likely failure layer with concise cause/recommendation text and measured evidence.
- Diagnostic run locking so two tests cannot compete for one ESP.
- Automatic restoration of saved camera settings/FPS, prior connection/stream state, and simulation state.

## Diagnosis categories

The classifier can report:

- `control_unreachable`;
- `firmware_incompatible`;
- `camera_not_ready`;
- `esp_camera_tcp_send_stall`;
- `direct_camera_stream_failure`;
- `control_stream_contention`;
- `pc_studio_stream_integration`;
- `control_plane_instability`;
- `wifi_margin_low`;
- `healthy_now`.

## Deliberate non-changes

- Existing V037/R6 ESP firmware is retained; V038 does not require another firmware flash.
- `aitl-camera-v037` / `aitl-tcp-jpeg-v1` compatibility is retained.
- No UDP transport, ESP-side AI, public-road control, or persistent diagnostic history is added.
- Diagnostics may temporarily apply the selected profile at 5 FPS, but the original saved profile values and selected state are restored after testing.

## Acceptance target

A user with a selected saved ESP camera can open Camera Test, press one button, wait for the staged run, and receive a useful layer-level diagnosis without a separate script or terminal command. Existing camera, simulation, inference and dataset workflows must remain intact.

## R2 detailed diagnostic hardening

The one-click Camera Test now measures three separate goals instead of only classifying a connection failure:

- **Functionality:** control/protocol/sensor readiness, configuration, start/stop, valid JPEG framing, concurrent control, reconnect, and normal PC Studio worker operation.
- **Stability:** 0–100 score using control failures, disconnects, invalid frames, polling failures, managed-worker failures, unexpected ESP send failures/deadlines, Wi-Fi transitions, FPS headroom, and frame-interval jitter.
- **Bottlenecks:** evidence-based attribution for HTTP control latency, Wi-Fi RF margin, throughput capacity, latency/jitter, control/data contention, ESP/TCP sender, and PC Studio receive integration.

The direct baseline remains 5 FPS. A bounded load phase also tests the saved target FPS up to 15 FPS without permanently changing the saved profile. Control latency reports average/p95/max; stream phases report throughput, payload size, FPS ratio, connection/first-frame timing, frame-interval average/p95/max/stddev, sequence gaps, invalid JPEGs, and disconnects. A deliberate receiver replacement verifies that the ESP accepts a new TCP client. Send failures caused by that intentional socket replacement are reported separately as diagnostic transition resets and excluded from unexpected-failure classification. The managed-worker phase now uses counter deltas measured only during that phase rather than lifetime counters.
