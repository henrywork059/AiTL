# API Contracts — current camera and junction-network highlights

## V0515 simulated-camera 3D preview (read-only)

`GET /api/camera/simulation/scene?source_id=simulation_camera` supports only the four saved simulation IDs: `simulation_camera`, `simulation_camera_b`, `simulation_camera_c`, `simulation_camera_d`. It returns the existing `{ok:true,data,meta:{request_id}}` envelope. Data includes `source_id`, `frame_number`, `received_at_ms`, `width`, `height`, `simulation_time_seconds`, `paused`, `density`, `signal:{phase,vehicle_go,pedestrian_walk,seconds_remaining}`, `vehicles:[{id,x,y,width,direction,vehicle_type,color}]` and `pedestrians:[{id,x,y,direction,color}]`. Positions are original 1280×720 camera-simulation coordinates; they are never converted to calibrated real-world 3D or physical camera viewpoints. Each A/B/C/D UI view uses a different orbit preset of the one shared scene. Invalid source IDs return 422 `CAMERA_SOURCE_INVALID`; simulation stopped returns 409 `CAMERA_STREAM_NOT_STARTED`. Reads refresh existing simulation state but do not configure/change signal policies. The legacy 2D frame/MJPEG APIs and AI, capture, region and ESP contracts remain unchanged.


## V0514 Network movement conflicts (simulation-only)

Crosswalk `network.links[]` accepts optional `movement_conflicts`: a unique array of `vehicle_vehicle`, `vehicle_pedestrian`, `pedestrian_vehicle`, `pedestrian_pedestrian` (ordered source/destination link endpoints). Invalid, repeated or unsupported values cause the existing 422 validation error. An omitted/empty array is backward-compatible and means no interlock for that link.

`GET /api/traffic/crosswalk-signals` now returns independent virtual signals projected through the Network interlock when conflicts are configured. Top level `coordination_enabled` and `movement_conflicts_configured` identify active virtual interlocking. Each node reports `coordination_status` (held/permitted/independent/unavailable), `coordination_reason` and optional `coordination_wait_seconds`. During hold, `signal.phase_key="coordination_hold"`, `phase="all_red"`, `vehicle_go=false`, `pedestrian_walk=false`, `seconds_remaining=0`, plus original requested phase and blocking crosswalk. A held node's local virtual clock does not progress until granted. No hardware command or new API route is added.

## V0512 emergency corridor follow-up

Saved Network links optionally accept `emergency_route` as `source_to_destination` or `destination_to_source`, with omission meaning Off. Multiple conflicting configured priority paths return 422. `GET /api/traffic/crosswalk-signals` may include the source/reason/expiry of a one-shot virtual emergency priority and now reports `coordination_enabled` when explicitly configured. No physical actuation endpoint is added.

## V0512 Automatic per-crosswalk camera observation bridge

No new endpoint. `GET /api/traffic/crosswalk-signals` retains the existing envelope and adds/updates each crosswalk's `observation_provenance: camera_ai|unavailable`, `camera_sources`, `camera_coverage: complete|partial|unavailable`, `region_class_counts`, and `source_timestamp_ms` when available. The response also includes `virtual_preview_enabled`; each source status may be `virtual` when real ESP camera AI drives software-only preview signals. No real hardware output occurs.

The running inference service maps each valid camera detection frame to saved Side A/B polygons and the corresponding independent **simulation** controller. It publishes per-class physical-region counts under both `region_id` and qualified `crosswalk_id:region_id` keys for existing scenario zone-class conditions. Counts for two recent synchronized views are averaged. Frames older than 5 seconds, models replaced/unloaded, unregistered/missing sources, and detection errors do not refresh observations. Valid frames with no objects produce zero counts.

`available_metrics` in controller observations explicitly declares calibrated metrics. Camera region-only observations set it empty, so pedestrian waiting, crossing and vehicle queue metrics cannot be inferred from generic polygons. Existing global traffic observation callers without this field retain previous behavior. No change to real traffic actuation or Network conflict coordination.


## V0511 Crosswalk signal controllers

`GET /api/traffic/crosswalk-signals` returns the standard request-ID envelope with `simulation_only`, `simulation_enabled`, `simulation_paused`, `coordination_enabled:false`, `movement_conflicts_configured:false`, `hardware_actuation_enabled:false`, and `crosswalks` keyed by existing saved Crosswalk ID. Each entry includes isolated `signal` (or null when simulation off), `controller_id`, `status`, `neighbors`, `observation_provenance` and `coordination_reason`. Each runtime uses the existing signal phase machinery. Legacy `/api/traffic/signal-status` is unaffected. Separate observation and test-input internal hooks are reserved for later camera mapping and coordination; not exposed as physical controls.


## V0510 timing and live adjustments

No new signal REST endpoints: `GET/PUT /api/traffic/signal-rules` persists both default timing and the new UI's ranked scenario templates. The backend `ALLOWED_METRICS` now accepts `phase_remaining_seconds` as an evaluated read-only metric, derived from the protected current phase. A rule can combine `pedestrians_crossing >= 1` and `phase_remaining_seconds <= 3` to request bounded clearance hold.

`GET /api/traffic/signal-status` remains a shared single simulation/prototype state; it is not a per-crosswalk controller. Network shows lamps only for the crosswalk assigned the current simulation source and marks other crosswalks unverified. Adjacent links provide advisory notices only; they do not change traffic signals or imply conflicts. Emergency class rules request protected phases through existing simulation rules; they do not flash vehicle green or command physical roads.


## V059 global camera inference (preview-only)

- `POST /api/models/upload?model_id=<safe-id>` accepts raw application/octet-stream .pt weights (limit 200 MiB), stores them as a new `outputs/training/<safe-id>/weights/best.pt` without overwrite and returns the standard model registry envelope. Reject invalid model IDs, duplicate IDs, empty or oversized uploads. Uploaded weights must still be explicitly loaded; unsupported model files can fail during activation.
- `DELETE /api/models/{model_id}` rejects deletion of the active model with 409; activation remains `POST /api/inference/load`.
- `PUT /api/settings/runtime` adds optional `inference_interval_ms` (100–2000; default 500) to existing persistent settings. `default_confidence` is the global inference threshold. `live_poll_interval_ms` continues to control camera status polling, not inference.
- `GET /api/inference/cameras/{source_id}` returns `{"source_id": "...", "frame": <detection-frame-or-null>, "error": <null-or-message>}` inside the normal API envelope. These observations originate in one background worker using the same active model across saved live ESP streams, saved simulated cameras and recent legacy frame receiver uploads. The worker processes newest available frames on a best-effort interval without queued backlogs and prevents stale results from appearing current.
- `GET /api/camera/preview/{source_id}` returns a current JPEG/PNG from a registered camera without changing active selection. Image responses retain X-Request-ID. The frontend counts classes only within the selected camera's configured Side A/B region polygons; cross-camera counts are *not* deduplicated or summed.
- The existing selected-source `GET /api/inference/detections`, `GET /api/traffic/state`, tracking, capture, signal rules and Network overview keep their previous single-current-source semantics; do not misrepresent global preview detections as traffic-controller observations.



## V057 Crossing Network graph (additive to Crosswalk schema 1)

`GET /api/crosswalks` and `PUT /api/crosswalks` continue using `schema_version: 1`. An **optional** `network` object contains `positions` (a map of saved crosswalk IDs to finite numeric x/y percentages 0–100) and `links` (at most 64 named crossing-to-crossing connections, with distinct existing source/destination crossing IDs and `source_edge`/`destination_edge` values 1–4). At most 32 saved crossing positions are permitted; duplicate or reverse-equivalent endpoint/edge connections are rejected with the existing CROSSWALK_INVALID (422) error, preserving the previously saved JSON. Older records without `network` round-trip unchanged.

A Network box is derived automatically from each saved `crosswalks[]` entry, whether or not its ID has an explicit position; the default visual layout is computed in the frontend. When a crosswalk is removed through Crosswalks, its visual links and position are removed in the same atomic save. Crossing names/camera assignments remain defined only in Crosswalks; Network does not introduce a second registry.

`GET /api/traffic/network/overview` adds `crosswalk_region_counts` from its existing selected-source traffic-state computation, without triggering a second detection pass. Network boxes display assigned camera connectivity; region counts are available only for a currently inferred source. Unobserved cameras have no fabricated occupancy. Connections represent configuration metadata only, not observed traffic transfers or live signal control. V059 background detection is separate from Network overview.

## V056 One physical region with two camera polygons

Each newly created crosswalk region is **one logical region** with a stable internal `id` and an editable shared `label`. It retains `vertices` for older clients and may contain `vertices_by_side: {"a": [[x,y], ...], "b": [[x,y], ...]}` (one or both keys; each polygon is a validated convex quadrilateral in the existing 1280 × 720 reference frame). Region Editor does not expose backend IDs. Side A and B coordinates are edited separately and saved atomically through the existing crosswalk PUT endpoint, without changing schema version 1. Missing `vertices_by_side` falls back to the legacy `vertices` polygon. Earlier side-scoped `camera_side: "a" | "b"` records remain side-scoped; their associations are not guessed or silently rewritten.

`GET /api/traffic/state` provides `crosswalk_region_counts` only for a camera source with a current inferred frame. Its keys `crosswalk_id:side:region_id` and `camera_region_id` distinguish the two camera views, while `physical_region_id` (`crosswalk_id:region_id`) links them to the **same physical area**. `class_counts` and `total` represent per-frame observations from one active camera; do **not** add A/B counts to infer unique pedestrians or vehicles without multi-camera identity matching. V059 runs independent background detection for multiple saved camera feeds, but does not perform inter-camera deduplication or physical signal control. This older traffic-state route remains selected-source-only.

## V054 Camera-specific regions and live counts

`camera_side` is optional on schema-1 crosswalk regions (`a` or `b`); missing values preserve legacy shared geometry. Per-frame active-source detections are counted by region under `crosswalk_region_counts` in `GET /api/traffic/state`, keyed `crosswalk:side:region`. Each result contains camera source, region ID, display label, per-class counts and total. The legacy traffic-state observation remains selected-source-only; V059 adds independent per-camera preview inference without signal policy changes.

## V0323 Crosswalk shared quadrilateral regions

Crosswalk schema version **remains 1**. Each crosswalk has an optional `regions` list (missing in older records means `[]`), up to 24 regions per crosswalk, with unique `id`, `label` (1–120 characters), and `vertices` holding exactly four integer `[x, y]` points. Coordinates use the editor's 1280 × 720 reference view (inclusive bounds) in clockwise or counterclockwise order; the outline must be a non-degenerate convex quadrilateral. Invalid data uses the existing `ATL-CROSSWALK-001` (422), and the prior data remains intact. Regions are shared crosswalk metadata, **not independently calibrated** for two physical camera perspectives and do not activate AI counting, inference or signal logic. No new endpoints.

Junction Network, Camera Sources and Crosswalks use the existing global camera simulation endpoints (`POST /api/camera/simulation/start` and `/stop`) and one shared simulated camera. A simulated junction does not create a simulated camera per crosswalk or per intersection. Physical ESP stream workers are paused by the existing camera service while simulation runs.

## V0320 Crosswalk configuration

`GET /api/crosswalks` returns `{"schema_version":1,"crosswalks":[]}` when empty. Crosswalk entries contain `id` (unique letter-first token, up to 64 chars), `label` (1–120 chars), `location` (0–160 chars), and nullable `camera_side_a_id` and `camera_side_b_id` source IDs.

`PUT /api/crosswalks` accepts `{"config":{"schema_version":1,"crosswalks":[...]}}` to atomically save the whole set (up to 32). Assigned camera IDs must have valid existing camera-source syntax and differ within a crosswalk; references to deleted saved cameras remain visible until deliberately reassigned. Crosswalk source IDs refer to the existing remote-camera registry and do not initiate streams.

Both routes use the standard request-ID success/error envelope. Invalid records return `ATL-CROSSWALK-001` (422); persisted read/write failures return `ATL-CROSSWALK-002/003` (500). This is configuration metadata only, not simultaneous multi-camera inference or traffic-signal control.


Existing non-described contracts remain unchanged. All JSON success/error responses retain the standard envelope and request ID conventions.

## V0324 Cardinal-edge crosswalk assignments

The existing schema-1 `intersections[]` record optionally includes:

```json
"crosswalk_edges": {
  "north": "crosswalk_1",
  "east": null,
  "south": "crosswalk_2",
  "west": null
}
```

Each of the four cardinal edge keys is optional on input; omitted keys and older records without `crosswalk_edges` normalize to `null`. Values are either `null` or a crosswalk ID matching the existing letter-first ID token syntax (1–64 chars). One crosswalk ID can belong to only one edge across the entire network. Unknown directions, invalid IDs and duplicates return `ATL-TRAFFIC-013` (422) without overwriting the previous JSON. Mappings are stored in the existing `config/intersections.json` file and returned by `GET /api/traffic/network` and the network overview; no new endpoint is introduced.

Crosswalk definitions continue to live in `config/crosswalks.json`. The backend deliberately retains a mapping to a deleted crosswalk for operator review, and the inspector marks it missing. Junction-edge mapping is configuration metadata only and does not modify real or simulated signal decisions.

## V0311 Junction Network configuration

`GET /api/traffic/network`

Returns the persisted logical intersection network plus `config_path`, `cooperative_control_active: false`, and `prototype_only: true`.

The existing schema remains `schema_version: 1`. V0311 extends each `intersections[]` object with:

```json
{
  "id": "junction_a",
  "label": "Junction A",
  "enabled": true,
  "source_ids": ["esp32_cam_01", "esp32_cam_02"],
  "primary_source_id": "esp32_cam_01",
  "zone_ids": [],
  "signal_profile": "Normal",
  "position": {"x": 28.0, "y": 42.0}
}
```

Rules:

- one junction may contain zero or more `source_ids` up to the existing configured maximum;
- one source id may appear in only one junction;
- `primary_source_id` is nullable and, when present, must be one of that junction's `source_ids`;
- `position.x` and `position.y` are finite logical canvas percentages from 0 through 100;
- older schema-1 records without `primary_source_id` or `position` remain accepted and receive deterministic defaults when normalized/saved;
- `links[]` retain the existing directed source/destination/approach/travel-time contract.

`PUT /api/traffic/network`

Body remains:

```json
{"config": {"schema_version": 1, "active_intersection_id": "...", "intersections": [], "links": []}}
```

Validation failures continue to use the existing traffic-network error contract. V0311 introduces no new stable error code.

`POST /api/traffic/network/reset`

Resets to the single default prototype junction using the same schema, including its default logical position and primary simulation source.

`GET /api/traffic/network/context?intersection_id=<id>`

Retains the existing per-junction topology context behavior. Configured neighbours remain metadata and do not activate live cooperative control.

## V0311 Junction Network overview

`GET /api/traffic/network/overview`

Returns one observational projection for the Junction Network page. The route is read-only; it does not start/stop cameras, mutate network configuration, run signal arbitration, or create additional inference pipelines.

Top-level data includes:

```json
{
  "schema_version": 1,
  "generated_at_ms": 0,
  "network": {},
  "available_cameras": [],
  "active_source_id": "esp32_cam_01",
  "current_frame_source_id": "esp32_cam_01",
  "observation_intersection_id": "junction_a",
  "observation_provenance": "ai_detection",
  "source_mapping_matched": true,
  "simulation_enabled": false,
  "junctions": [],
  "links": [],
  "warnings": [],
  "summary": {},
  "multi_camera_assignment": true,
  "simultaneous_multi_junction_inference": false,
  "prototype_only": true,
  "scope_note": "..."
}
```

`available_cameras[]` projects saved ESP camera status including source id, host, selected/connected/reachable/streaming state, measured FPS, last success/error and a compact state label.

Each `junctions[]` entry includes persisted identity/layout/source metadata plus:

- assigned camera summaries;
- `camera_count`, `reachable_camera_count`, and `streaming_camera_count`;
- `live.vehicle` total/waiting/load;
- `live.pedestrian` total/waiting/crossing/load;
- current phase/decision/decision reason where available;
- structured event records for current ranked scenario, protected service request, manual/test input or observed crossing activity where supported by the existing live decision context;
- warnings for missing/unassigned source profiles, unavailable assigned ESPs, camera errors, offline primary camera, unmapped current source, or unavailable live traffic observation.

The live-data rule is strict: PC Studio still has one shared selected camera/simulation inference pipeline. Only the junction resolved from the current frame/source receives current live traffic metrics and decision context. Other configured junctions return `observation_provenance: "unavailable"` and unavailable load instead of copying the selected junction's occupancy. Camera assignment does not imply multi-camera fusion, cross-camera identity matching, observed network transfer, emergency recognition, or active cooperative signal control; V059 independently infers camera preview frames without changing this overview.

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

V0310 keeps this wire format but tunes the production ESP capture/send implementation; V0311 does not change that transport.

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

Several ESP streams may be active simultaneously. Each has its own TCP worker and newest-frame cache. Only the selected ESP publishes into the existing global `CameraFrameService`; Dataset Capture, zones, legacy inference/tracking and analytics continue to consume one unambiguous active source. V059 Camera AI Preview separately reads the per-camera background inference worker. Selecting another already-running ESP promotes its cached newest frame only when it was received recently; otherwise the previous physical frame is cleared and the shared pipeline waits for the next fresh frame from the selected ESP.

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
