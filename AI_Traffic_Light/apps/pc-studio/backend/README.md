# PC Studio Backend

`RemoteCameraService` owns one physical ESP transport lifecycle. `RemoteCameraManager` owns the saved multi-camera registry and active-source selection:

- persistent per-camera IP/source/FPS/OV2640 profiles under runtime `config/remote_cameras.json`;
- independent status/control-only Connect per saved ESP;
- serialized/retried low-rate HTTP control requests;
- PC-owned camera configuration;
- persistent length-prefixed TCP JPEG transport from ESP port 81;
- PC TCP keepalive, `TCP_NODELAY`, read timeout and reconnect lifecycle;
- exact fixed-header/frame reads with JPEG validation;
- event notification for the browser preview relay;
- bounded exponential reconnect backoff;
- automatic ESP session recovery after reset/loss;
- per-ESP newest-frame caches so several streams may stay active while exactly one selected ESP feeds the shared downstream frame service;
- freshness-guarded source switching so stale caches/old-IP frames cannot masquerade as a new selected frame;
- backend lifespan shutdown that disconnects every active ESP session.

`CameraFrameService` remains the common downstream latest-frame surface used by preview, inference, dataset capture, zones and analytics. `GET /api/camera/live.mjpeg` remains browser-facing MJPEG; the ESP→PC image hop uses the `aitl-tcp-jpeg-v1` fixed-header JPEG stream.

The current quality-preserving camera firmware preserves saved image quality/resolution under transport pressure. New profile defaults remain QVGA / JPEG 24 / 15 FPS; existing persisted profiles are not replaced by source patches.

## Simulation timing and safety

`CameraFrameService` advances synthetic vehicles and pedestrians in up-to-50 ms integration substeps, capped at 2 seconds of catch-up per update. Each substep obtains one stateful protected phase from `SignalRulesService.signal_state` and uses that **same snapshot** for vehicle and pedestrian movement. This avoids duplicating phase/scenario evaluation and prevents mismatched agent movement decisions at the same simulation time. The controller, not the renderer, remains responsible for yellow, all-red, pedestrian WALK/CLEAR and other protected timing rules.

The current render's BGR canvas is also reused for alternate synthetic camera PNGs; no canonical frame or 3D coordinates are changed. These optimizations concern **simulation-only** movement and rendering, not real ESP image transport or physical traffic-light actuation. To verify them, from `AI_Traffic_Light/` run `python scripts/test_camera_frame_service.py` and `python scripts/test_signal_rules_service.py`; full candidate validation and owner Windows tests are documented in `docs/LOCAL_TESTING.md`.

## Camera diagnostics

`CameraDiagnosticService` owns the one-click diagnostic workflow exposed through `POST /api/camera/diagnostics/run`. It measures the selected saved ESP through direct control probes, direct ATL1/JPEG receiving, direct receiving with concurrent status polling, and the normal manager/service stream path. It returns measured checks plus an evidence-based likely-failure classification and restores the prior selected-camera/simulation state where possible. The diagnostics service does not own traffic-signal logic or physical/public-road authority.
V038 R2 Camera Diagnostics also measures per-phase stream deltas, throughput/FPS headroom, frame timing/jitter, reconnect behavior, and bottleneck attribution while restoring the previous camera state.
