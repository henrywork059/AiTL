# API Contracts (current highlights)

All JSON API responses use the standard success/error envelopes and `meta.request_id`. Binary/image/CSV responses preserve `X-Request-ID`.

## Camera

### Existing camera/simulation surface

- `GET /api/camera/sources`
- `GET /api/camera/status`
- `GET /api/camera/frame`
- `POST /api/camera/frame?source_id=<camera_id>`
- `POST /api/camera/simulation/start`
- `POST /api/camera/simulation/stop`
- `POST /api/camera/simulation/settings`

`POST /api/camera/frame` accepts a raw JPEG/PNG body and remains the backward-compatible ESP/Raspberry-Pi push transport.

`GET /api/camera/frame` returns the latest device/remote/simulation frame as image bytes with `X-Request-ID`, `X-Camera-Source`, and `X-Frame-Number`.

When simulation is active, camera status includes the synthetic signal phase/countdown, cycle information, and simulation controls. Simulation remains local/test-only.

### V032 remote ESP32-CAM pull

- `GET /api/camera/remote/status`
- `POST /api/camera/remote/connect`
- `POST /api/camera/remote/disconnect`

Connect body:

```json
{
  "host": "192.168.1.87",
  "source_id": "esp32_cam_01",
  "fetch_interval_ms": 500
}
```

Rules:

- `host` must be a literal IPv4 address in `10/8`, `172.16/12`, or `192.168/16`;
- hostnames, loopback, link-local, IPv6, and public IP addresses are rejected;
- `source_id` uses 1–64 letters/numbers/dot/dash/underscore;
- fetch interval is 100–5000 ms;
- the backend probes `GET http://<host>/capture` before establishing the connection and does not follow HTTP redirects;
- the stock CameraWebServer response must be a valid JPEG no larger than the existing 8 MiB frame limit;
- the remote worker ingests snapshots through the existing `CameraFrameService`;
- while built-in camera simulation is active, remote ingestion pauses and resumes after simulation stops;
- configuration is process-memory only in V032.

Remote status includes:

- `configured`, `worker_running`, `connected`, `paused_for_simulation`;
- `host`, `source_id`, `capture_url`, `stream_url`;
- interval/start/attempt/success timestamps;
- last HTTP/frame metadata;
- successful/failed fetch counts;
- last error and `prototype_only`.

The returned stream URL is the stock CameraWebServer `http://<host>:81/stream`. Browser preview is presentation-only; the backend processing path uses `/capture` snapshots.

No new stable error code is introduced. V032 reuses camera/request errors, notably `ATL-CAMERA-001`, `ATL-CAMERA-003`, `ATL-CAMERA-005..007`, and `ATL-API-002`.

## Dataset / zones

Existing dataset capture/list/delete/label/build endpoints and zone endpoints remain unchanged. Supported zones remain `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, `counting_line`, and `ignore`. Counting lines require two distinct points and are analytics-only.

Dataset Capture consumes the current `CameraFrameService` frame, so a connected V032 ESP frame can be persisted through the existing capture workflow without a new dataset contract.

## Inference

Existing inference/model endpoints remain unchanged. Local inference runs on the latest PC-side camera frame. V032 transports camera images only; it does not add ESP-side inference or claim any new detector class/accuracy.

## Traffic state

- `GET /api/traffic/state`

Returns current occupancy/zone/class observations plus detection-driven recommendation data. Existing fields include intersection identity, observation provenance, network context and structured decision context.

Occupancy remains sampled presence. Track-derived flow remains separate.

## Signal rules / traffic logic

Existing signal-rule endpoints remain unchanged:

- `GET/PUT /api/traffic/signal-rules`
- `POST /api/traffic/signal-rules/reset`
- `POST /api/traffic/signal-rules/runtime/reset`
- `POST /api/traffic/signal-rules/test-inputs`
- `POST /api/traffic/signal-rules/incident/clear`
- `POST /api/traffic/signal-rules/preview`
- `GET /api/traffic/signal-status`
- `GET /api/traffic/signal-rules/history`
- `DELETE /api/traffic/signal-rules/history`

Ranked scenarios remain controller-owned. Exactly one highest-ranked eligible scenario wins an evaluation; phase order/minimum/maximum/cycle protections remain unchanged.

## Occupancy / tracking / flow

Existing endpoints remain:

- `GET /api/traffic/history`
- `GET /api/traffic/history/export.csv`
- `DELETE /api/traffic/history`
- `GET /api/traffic/tracks`
- `GET /api/traffic/flow`
- `GET /api/traffic/flow/export.csv`
- `DELETE /api/traffic/flow`

Unique passages are track/counting-line events, not occupancy counts.

## Intersection/network foundation

Existing endpoints remain:

- `GET /api/traffic/network`
- `PUT /api/traffic/network`
- `POST /api/traffic/network/reset`
- `GET /api/traffic/network/context`

The network configuration remains generic for multiple intersection/source identities and directed links. Live/runtime links are topology metadata; they do not by themselves activate live cross-camera cooperation.

## Single-junction experiments

Existing endpoints remain:

- `POST /api/traffic/experiments`
- `GET /api/traffic/experiments`
- `GET /api/traffic/experiments/{run_id}`
- `DELETE /api/traffic/experiments/{run_id}`
- `GET /api/traffic/experiments/{run_id}/export.csv`

These are isolated seeded synthetic Fixed-vs-Adaptive comparisons and do not mutate the live camera/controller runtime.

## Network experiments

Existing endpoints remain:

- `POST /api/traffic/network-experiments`
- `GET /api/traffic/network-experiments`
- `GET /api/traffic/network-experiments/{run_id}`
- `DELETE /api/traffic/network-experiments/{run_id}`
- `GET /api/traffic/network-experiments/{run_id}/export.csv`
- `GET /api/traffic/network-experiments/{run_id}/evidence`
- `GET /api/traffic/network-experiments/{run_id}/evidence.csv`

The current seven comparison/ablation modes remain:

1. Fixed;
2. Independent Adaptive;
3. Cooperative Adaptive;
4. Pedestrian-aware Cooperative;
5. Class-aware Cooperative;
6. Emergency Baseline Cooperative;
7. Emergency-priority Cooperative.

All neighbour transfer/prediction/cooperation, pedestrian-awareness, class profiles/priorities, and emergency event/priority evidence in these network experiments remains synthetic simulator evidence.

Protected network-overlay arbitration remains:
`incident_hold > pedestrian_crossing > emergency_priority > pedestrian_max_wait > vehicle_class_priority > network_cooperation`.

V031 `decision_evidence` remains schema-versioned normalized read/export evidence over the detailed experiment histories. V032 does not alter those experiment contracts.

## Training / models / settings / logs

Existing training status/start, managed dataset, model registry/load/default/delete, runtime settings and recent log endpoints remain unchanged.

## Safety boundary

No V032 API sends commands to physical/public-road traffic infrastructure. Remote ESP32-CAM integration is input transport only. Signal scenarios and network experiments remain simulation/recommendation/evaluation surfaces.
