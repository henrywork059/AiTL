# Architecture

AiTL is a local/student-scale computer-vision and traffic-light simulation prototype. No layer sends commands to physical/public-road traffic infrastructure.

## 1. Live single-intersection path

```text
ESP-CAM / uploaded receiver frame / synthetic camera
                ↓
          CameraFrameService
                ↓
        local inference/tracking
                ↓
 zones + occupancy/flow/class observations
                ↓
       traffic-state evaluation
                ↓
 ranked signal-scenario controller
                ↓
 protected simulated phase/recommendation
                ↓
 PC Studio + analytics + capture/explanation
```

`signal_rules.py` owns arbitration and protected phase timing. Other services may supply observations/context but must not reimplement controller authority.

## 2. Isolated Simulation Lab path

```text
saved profile + zones + density + seed
        ↙                     ↘
 Fixed numeric simulator    Adaptive numeric simulator
 + isolated controller     + isolated controller
        ↘                     ↙
       aligned synthetic telemetry
```

Experiment controllers/agents are separate from the live camera/controller runtime.

## 3. Network/explanation foundation and V026 experiment path

```text
camera/source id
      ↓
IntersectionNetworkService
      ↓
intersection identity + configured directed links
      ↓
traffic API enrichment
      ↓
DecisionContext projection
```

The network service persists generic topology metadata under runtime `config/intersections.json`. The explanation service projects current traffic/signal/network state into structured context. Those live services still do not create a second live signal controller.

V026 adds a separate isolated experiment path:

```text
seeded exogenous demand + configured directed link
              ↓
   Intersection A experiment runtime
      + SignalRulesService A
              ↓ synthetic serviced transfer
      deterministic travel pipeline
              ↓
   Intersection B experiment runtime
      + SignalRulesService B
              ↓
 per-intersection + network telemetry
```

`network_simulation_experiments.py` owns this path. It creates separate controller instances and explicit synthetic transfer events without touching the live camera/controller runtime.

Live configured links remain **metadata**, not observed transfers. V026 experiment transfer is synthetic simulator evidence. Cooperative/emergency-active flags remain false.

## 4. Planned cooperative multi-intersection architecture

The next architecture step reuses the V026 independent baseline instead of creating a parallel controller:

```text
Intersection A runtime ── predicted/scheduled arrival context ──► Intersection B runtime
       │                                                          │
 SignalRulesService A                                        SignalRulesService B
       │                                                          │
       └──────────── explicit neighbour evidence layer ────────────┘
                                ↓
          Fixed / Independent Adaptive / Cooperative comparison
```

Requirements before cooperation is considered implemented:

- neighbour/arrival context enters bounded ranked-scenario evaluation;
- protected local phase rules remain controller-owned;
- decisions record the neighbour evidence used;
- deterministic tests show neighbour context changes an eligible decision;
- network metrics compare against the V026 independent-control baseline.

## 5. Backend ownership

```text
apps/pc-studio/backend/app/
  main.py                 FastAPI wiring only
  models.py               Pydantic contracts
  core/                   envelope/error/logging/middleware/version/persistence helpers
  routes/                  HTTP translation
  services/                domain behavior/state/persistence/inference/training
```

Important services:

- `camera_frames.py` — latest receiver frame + synthetic camera runtime;
- inference service — trained-model inference;
- `object_tracking.py` / `traffic_flow.py` — prototype tracking/flow;
- `zones.py` / `traffic_history.py` — zone config/occupancy;
- `signal_rules.py` — ranked scenarios + protected simulated timing;
- `simulation_experiments.py` — isolated deterministic single-junction Fixed-vs-Adaptive experiments;
- `network_simulation_experiments.py` — isolated two-intersection independent-control experiment + synthetic link transfer;
- `intersection_network.py` — intersection/source/topology metadata;
- `decision_context.py` — non-controlling structured explanation.

## 6. Frontend ownership

React/Vite PC Studio keeps `App.tsx` for top-level composition, pages for page behavior, components for reusable presentation, API modules for HTTP, shared types for contracts, and serial polling for non-overlapping periodic async refresh.

Dense experiment/explanation data should be grouped rather than rendered as an unbounded dashboard.

## 7. Data semantics

- occupancy = sampled presence;
- flow = track-derived events;
- zone/class counts = per-frame scenario observations;
- Simulation Lab telemetry = synthetic isolated output;
- live network links = configuration metadata; V026 network-experiment transfer = synthetic simulator events over a selected configured link;
- observation provenance = AI/simulation/manual/unavailable source classification.

Do not silently convert one category into another.

## 8. Device-camera role

Camera nodes capture/upload frames and expose simple device status/settings. Heavy inference, model training, signal scenarios, analytics, network cooperation, and experiment logic stay on the PC side.

## 9. Capability and safety boundaries

See `PROJECT_SCOPE.md` for implemented/foundation/planned status. Multi-intersection cooperation and emergency priority require additional simulator/controller evidence. All signal phases/actions remain prototype/simulation outputs; public-road control is outside scope.
