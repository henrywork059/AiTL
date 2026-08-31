# API Contracts — V037 camera transport highlights

Existing non-camera contracts remain unchanged.

## Connect

`POST /api/camera/remote/connect`

Connect probes ESP `/status` only and transfers zero image bytes.

The ESP must report:

```json
{
  "protocol": "aitl-camera-v037",
  "stream_protocol": "aitl-tcp-jpeg-v1",
  "camera_ready": true
}
```

V037 PC Studio also accepts `aitl-camera-v036` because V036 uses the same `aitl-tcp-jpeg-v1` wire format. A mismatched older firmware such as V035 returns the existing camera-not-connected error envelope with HTTP 409 and compatibility details. No new stable error code is introduced.

## Start

`POST /api/camera/remote/start`

Body contains:
- `target_fps` 1–30;
- the complete OV2640 settings object;
- legacy `fetch_interval_ms` remains accepted as a compatibility alias.

Ordering:

```text
/stop best effort
/config?<settings + stream_fps>
/start
persistent TCP connect to ESP :81
```

## Persistent image transport

ESP port 81 is not HTTP in V037/V036. It is one private-LAN TCP stream with repeated frames:

```text
ATL1 | uint32 JPEG length | uint32 sequence | uint32 ESP uptime_ms | JPEG bytes
```

All integer fields are unsigned network byte order. Payload length must be 1..`MAX_FRAME_BYTES`. JPEG SOI/EOI markers are validated before storage.

The backend uses exact header/payload reads. On transport failure it probes `/status`; if `session_active=false`, it reapplies retained configuration and `/start` before reconnecting.

## Browser preview

`GET /api/camera/live.mjpeg`

This HTTP endpoint remains multipart MJPEG. It relays the latest PC-side frame; the browser does not connect to the ESP binary stream directly. Physical frame delivery remains event-driven.

Response disables caching/transformation/buffering where supported.

## Remote status

`GET /api/camera/remote/status`

Existing fields remain, with these V037 semantics/additions:

- `transport`: `idle` or `tcp_jpeg`;
- `stream_protocol`: `null` or `aitl-tcp-jpeg-v1`;
- `stream_url`: `tcp://<private-ip>:81` when configured;
- `source_sequence_gaps`: inferred missing ESP source sequence values;
- `last_remote_sequence`;
- `last_source_uptime_ms`;
- existing connection/recovery/FPS/byte fields remain.

Private RFC1918 IPv4 restriction remains. No redirects or public-road signal-control API are introduced.


## Saved multi-camera registry

The saved multi-camera registry retained from V036 provides:

- `POST /api/camera/remote/cameras` — save/update one ESP profile (`host`, `source_id`, `target_fps`, complete settings) and select it;
- `POST /api/camera/remote/select` — select an existing saved ESP without stopping other ESP streams;
- `DELETE /api/camera/remote/cameras/{source_id}` — stop/disconnect that ESP if needed and remove its saved profile.

`GET /api/camera/remote/status` remains backward compatible for the selected camera and additionally returns `active_source_id`, `camera_count`, `cameras`, `multi_camera`, and `max_saved_cameras`. Each `cameras[]` item reports its saved IP/settings plus connected/streaming/reachability state.

Profiles are stored locally in `config/remote_cameras.json` using the existing atomic JSON-store helper. Socket state is never persisted: after PC Studio restarts, the list/settings are restored but devices must be connected again.

Several ESP streams may be active simultaneously. Each has its own TCP worker and newest-frame cache. Only the selected ESP publishes into the existing global `CameraFrameService`; therefore Live AI, Dataset Capture, zones and analytics continue to consume one unambiguous active source. Selecting another already-running ESP promotes its cached newest frame only when it was received recently; otherwise the previous physical frame is cleared and the shared pipeline waits for the next fresh frame from the selected ESP.


## V037 R6 quality-preserving transport telemetry

A V037 R6 device `/status` additionally reports:

- `quality_preserving_transport: true`;
- `adaptive_quality_enabled: false`;
- `configured_jpeg_quality` and `effective_jpeg_quality` (R6 keeps them equal);
- `configured_frame_size` and `effective_frame_size` (R6 keeps them equal);
- `send_ewma_ms`: exponentially weighted send time;
- `transport_slow_frames`: frames whose send time exceeded the requested frame-period budget;
- `wifi_bssid` and `wifi_channel`: current AP identity/channel alongside existing `rssi`;
- `wifi_disconnects` and `wifi_reconnects`: ESP-side connection transition counters;
- existing `last_frame_width` / `last_frame_height`, frame byte count and send diagnostics.

For same-candidate compatibility, the previous `adaptive_quality_adjustments`, `adaptive_payload_target_bytes`, `adaptive_local_frame_drops`, `adaptive_window_learns`, `adaptive_resolution_downshifts`, and `adaptive_resolution_recoveries` keys remain present but stay zero in R6. They must not be interpreted as active adaptation.

These fields are diagnostic device telemetry. They do not change the `ATL1` image packet format or PC-side API envelopes.


## V038 one-click camera diagnostics

`POST /api/camera/diagnostics/run`

No request body is required. The endpoint diagnoses the currently selected saved ESP camera. If no saved camera is selected, it returns the existing camera-not-connected error envelope with HTTP 409; V038 introduces no new stable error code.

The route delegates staged testing and state restoration to the camera diagnostic dispatch/service layer. A successful standard-envelope response contains a report with `run_id`, `source_id`, `host`, `overall`, `diagnosis_code`, `title`, `summary`, `confidence`, `checks`, `metrics`, `likely_causes`, `recommendations`, `state_restored`, `restore_error`, `diagnostic_target_fps`, and `prototype_only`.

The diagnostic stages are: repeated direct ESP `/status` probes; firmware/wire-protocol and camera-readiness checks; RSSI/BSSID/channel inspection; direct `ATL1`/JPEG receiving that bypasses the normal PC Studio stream worker; direct receiving while `/status` polling runs concurrently; the normal `RemoteCameraManager` / `RemoteCameraService` managed stream; and restoration of the prior camera/simulation state.

The measurement stream uses the selected profile's saved image settings at a conservative 5 FPS. The service then restores the original saved FPS/settings and prior connected/streaming/simulation state. Diagnostic evidence does not change the `ATL1` packet format, the R6 quality-preserving ESP behavior, or public-road/signal-control authority.

### V038 R2 detailed camera-diagnostic evidence

`POST /api/camera/diagnostics/run` retains the existing envelope and adds detailed report sections: `functionality`, `stability`, and `bottlenecks`. Metrics include control average/p95/max latency, direct-stream sequence gaps and p95 frame interval, bounded load target/achieved FPS and throughput, reconnect result/timing, managed-worker per-phase FPS/counters, total versus unexpected ESP send failures, and diagnostic transition resets. The diagnostic remains state-restoring and does not persist test FPS/settings.

### V038 integrated benchmark and timing follow-up

When the selected ESP reports the R5 transport-benchmark firmware prefix, the same `POST /api/camera/diagnostics/run` action dispatches to the comprehensive transport benchmark rather than rejecting the firmware as production-incompatible. The response additionally includes `transport_benchmark` with the full snapshot/MJPEG/ATL1/DRAM/synthetic/UDP result matrix and may include `pipeline_timing`.

`pipeline_timing` is diagnostic-only evidence for the recommended passing transport. It reports the target frame period, observed frame interval, ESP-reported camera acquisition and socket-send timing samples, the portion of the interval explained by capture+send, the still-unexplained interval, a short independent `/capture` timing probe, comparison rows for direct plain-send / DRAM-copy / synthetic controls when available, a ranked `dominant_remaining_stage`, confidence, conclusions and the next targeted action. It does not claim firmware-level allocation/copy timing unless those timers are actually present.

The integrated timing follow-up intentionally reuses the already-flashed R5 firmware and does not require an ESP reflash. It adds four independent `/capture` samples after the broad matrix and compares each PC-observed request time with the firmware's existing `last_capture_ms` telemetry. A complete but under-target stream is not treated as fully stable merely because all requested frames arrived; target sustainability requires at least 70% of the requested FPS in the benchmark report mapping.

### V038 R8 payload and receiver alternative isolation

When an R5 transport-benchmark report is available, the same one-click action additionally runs a focused R8 follow-up without changing ESP firmware. It derives a reference payload from the median real streaming JPEG sizes rather than from the first `/capture`, then adds exact synthetic internal-DRAM payload tests at 5/10/15/reference/20/25 KiB-class sizes, four PC `SO_RCVBUF` requests, and a fast-versus-artificially-throttled PC receiver-drain A/B. The appended rows remain diagnostic controls and are not automatically promoted into production transport choices.

The response may include `alternative_analysis` and `transport_benchmark.alternative_analysis`. These report the reference real-JPEG byte size, exact-size synthetic-versus-real FPS, payload-size curve, receive-buffer sensitivity, receiver-drain sensitivity, findings, assessed alternatives and a next action. The analysis uses the already-benchmarked HTTP/MJPEG `WiFiClient.write()` paths, ATL1 plain `send()`, staged DRAM, UDP and assessment-only WebSocket/RTSP evidence where relevant. Runtime `SO_SNDBUF` tuning is not reported as tested because ESP-IDF/lwIP does not support changing that option by default. Lower-level raw lwIP `tcp_write`/`tcp_output` remains a future firmware A/B rather than a current implemented path.

### V038 R9 architecture bottleneck isolation

When the selected ESP reports firmware beginning `aitl-0_3_8-r9-architecture-benchmark`, the same `POST /api/camera/diagnostics/run` action dispatches to the focused R9 architecture benchmark. R9 requires the dedicated diagnostic sketch to be flashed first; it is not part of normal production firmware and it does not change the production camera protocol.

R9 physically compares six paths on the same ESP, camera, access point and PC:

- manual `WiFiServer` / `WiFiClient` multipart MJPEG, representing the current/R5-style Arduino writer;
- `esp_http_server` + `httpd_resp_send_chunk()` direct MJPEG, reproducing the older V035 server architecture;
- a FreeRTOS newest-frame producer/cache feeding `esp_http_server`, modeling the Pi-style decoupled producer/consumer design;
- camera-free `esp_http_server` bulk TCP;
- camera-free raw `WiFiClient` bulk with `TCP_NODELAY` enabled;
- camera-free raw `WiFiClient` bulk with Nagle enabled.

The R9 camera configuration restores the older PSRAM-capable two-framebuffer `CAMERA_GRAB_LATEST` strategy for the HTTPD comparison. `/status` also exposes the effective framebuffer count/location/grab mode, HTTPD readiness, reset reason including software brownout evidence, RSSI/BSSID/channel and memory telemetry. Reset reason is evidence only; R9 does not measure supply voltage and a non-brownout reset does not prove that the power rail never sagged.

A successful R9 response additionally includes `architecture_analysis` and `transport_benchmark.architecture_analysis`. The classifier can report `manual_socket_sender_regression`, `capture_send_coupling`, `camera_or_jpeg_pipeline_specific`, `common_network_or_esp_stack_bottleneck`, `httpd_architecture_healthy`, or `mixed_architecture_bottleneck`. Camera-free bulk below 1 Mbit/s is treated as evidence that the slowdown exists outside OV2640/JPEG work; camera-free bulk at or above 5 Mbit/s is treated as substantial common-path headroom. A 1.5x or greater HTTPD/manual frame-rate advantage is evidence against the manual socket writer, while a 1.5x or greater cached/direct advantage at useful target throughput is evidence for capture/send coupling. These thresholds are diagnostic heuristics, not release criteria.

R9 does not automatically replace ATL1, promote a firmware architecture, modify saved camera profiles permanently, add a stable error code, or grant physical/public-road signal-control authority. Any transport chosen from R9 evidence still requires a normal production-firmware patch and the usual owner acceptance workflow.

`GET /api/camera/diagnostics/progress`

Returns the same standard success envelope with the current diagnostic progress snapshot. Fields include `status`, `engine`, `stage`, `current_test`, `test_index`, `frame_current`, `frame_total`, `detail`, `last_line`, `started_at_ms`, `elapsed_ms`, `error`, and a bounded `log_tail`. `engine` may now be `architecture_benchmark` while R9 is active. Progress polling is observational only and does not start, stop or mutate a diagnostic run.