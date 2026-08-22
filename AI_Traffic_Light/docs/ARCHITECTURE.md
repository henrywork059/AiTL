# Architecture

## Current V025 prototype architecture

AiTL is a local/student-scale traffic-light computer-vision and simulation prototype. No layer sends commands to physical/public-road traffic infrastructure.

```text
ESP-CAM / uploaded receiver frame / synthetic camera
                ↓
          CameraFrameService
                ↓
       local inference / tracking
                ↓
      zones + per-class observations
                ↓
          traffic state evaluation
                ↓
      ranked signal-scenario controller
                ↓
 protected simulated phase / recommendation
                ↓
       PC Studio + analytics + capture
```

The isolated Simulation Lab uses separate numeric agents and separate controller instances so Fixed-vs-Adaptive experiments do not reset the live Camera Sources simulation/controller runtime.

## Same-candidate network foundation

V025 now also contains a configuration-only network layer:

```text
camera/source id
      ↓
IntersectionNetworkService
      ↓
intersection identity + configured links/neighbours
      ↓
traffic API enrichment
      ↓
structured decision context
```

`IntersectionNetworkService` persists generic intersection metadata under runtime `config/intersections.json` and supports up to the validated limits without assuming exactly two intersections. Each configured intersection may declare source ids, zone ids, a signal profile name, and enabled state. Directed links describe source/destination intersections, approaches, and an optional prototype travel-time estimate.

This foundation does **not** yet run more than one active live controller, transfer vehicles between intersections, predict arrivals, coordinate green windows, or implement emergency pre-emption. `cooperative_control_active` and `emergency_priority_active` remain false. The purpose is to establish stable identities/topology before later multi-intersection simulation work.

## Structured decision context

`GET /api/traffic/state` keeps the existing V025 traffic-state fields and adds network/explanation metadata at the API boundary:

- `intersection_id`;
- `observation_provenance` (`ai_detection`, `simulation`, `manual_test`, or `unavailable`);
- `network_context` with configured neighbours;
- `decision_context` with a deterministic decision id, trigger category, active ranked scenario/observed conditions when available, requested service, timing, pedestrian/vehicle context, emergency placeholder state, neighbour context, and a human-readable explanation.

Existing `outputs/signal_rules/decision_history.jsonl` remains the authoritative persisted controller-event history. The V025 network foundation does not create a second controller or claim historical causal reconstruction from the live decision context.

## Backend ownership

```text
apps/pc-studio/backend/app/
  main.py                 FastAPI app/wiring only
  models.py               Pydantic API/request models
  core/                   envelopes, errors, logging, middleware, atomic JSON helpers, version metadata
  routes/                  HTTP translation only
  services/                domain behavior/state/persistence/inference/training
```

Important service ownership includes:

- `camera_frames.py` — latest receiver frame and single-junction synthetic camera runtime;
- `inference.py` — local trained-model inference;
- `object_tracking.py` / `traffic_flow.py` — prototype tracking and flow events;
- `zones.py` / `traffic_history.py` — zone configuration and occupancy history;
- `signal_rules.py` — ranked scenario arbitration and protected simulated phase timing;
- `simulation_experiments.py` — isolated deterministic Fixed-vs-Adaptive experiments;
- `intersection_network.py` — persistent generic intersection/topology metadata only;
- `decision_context.py` — non-controlling structured live explanation projection.

## Frontend ownership

PC Studio remains React/Vite. `App.tsx` coordinates navigation/top-level state, pages own page behavior, reusable components own presentation, `api.ts` owns typed domain calls, and `useSerialPolling` prevents overlapping async poll loops.

The network foundation is backend/API-first in this same-candidate update; a dedicated multi-intersection visual editor/simulator is intentionally deferred until a later candidate.

## Data semantics

- Occupancy is sampled presence, not throughput.
- Unique passage requires prototype track identity plus a counting-line event.
- Zone/class counts are per-frame scenario observations.
- Network links are configured metadata, not evidence of observed vehicle transfer.
- Simulation Lab telemetry is synthetic benchmark data and is isolated from live occupancy/flow history.
- Manual Test-mode accessibility/incident flags must remain explicit manual/simulation sources.

## Device camera role

ESP32/Raspberry Pi camera nodes remain lightweight frame sources. They may connect to Wi-Fi, capture frames, and upload JPEG/PNG data to PC Studio. Heavy inference, model training, ranked signal logic, network cooperation, and analytics belong on the PC side.

## Safety boundary

All phases, scenarios, topology links, neighbour context, emergency placeholders, and decision explanations are local prototype/simulation/recommendation data. Physical/public-road signal control remains outside project scope.
