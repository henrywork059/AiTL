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

## 3. Network/explanation foundation and V027 experiment path

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

The network service persists generic topology metadata under runtime `config/intersections.json`. The explanation service projects current traffic/signal/network state into structured context. These live services still do not create a second live signal controller.

V027 keeps the isolated experiment path and adds a bounded cooperation layer:

```text
same seeded exogenous demand
              ↓
   Intersection A experiment runtime
      + SignalRulesService A
              ↓ synthetic serviced transfer
      deterministic travel pipeline
              ↓ predicted arrival context
   Intersection B experiment runtime
      + SignalRulesService B
              ↓
 bounded protected coordination advisory
              ↓
 per-intersection + network + coordination telemetry
```

`network_simulation_experiments.py` owns this isolated path. It creates separate controller instances, explicit synthetic transfer events, and a simulation-only downstream coordinator without touching live camera/controller runtime.

### V027 comparison modes

- **Fixed** — configured normal timing.
- **Independent Adaptive** — local ranked scenarios only.
- **Cooperative Adaptive** — the same local adaptive controller plus neighbour-informed bounded timing advisories at the downstream intersection.

The coordinator does not replace `SignalRulesService`, does not reorder phases, and does not write a second signal policy. It may extend vehicle green only within saved phase/cycle caps or request earlier protected progression toward vehicle service. Active pedestrian demand blocks cooperation-driven shortening of pedestrian WALK/CLEAR.

Live configured links remain **metadata**, not observed transfers. V027 transfer, predicted-arrival, and coordination events are synthetic simulator evidence. Emergency priority remains inactive.

## 4. Later cooperative-network generalization

V027 proves bounded cooperation for one selected directed pair. Later work may generalize experiment orchestration to multiple simultaneous links/intersections while preserving:

- one independent controller runtime per intersection;
- explicit neighbour evidence and provenance;
- protected local phase ownership;
- pedestrian/emergency guards;
- deterministic comparisons against Fixed and Independent Adaptive baselines;
- network-level metrics rather than only local wins.

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
- live network links = configuration metadata; V027 network-experiment transfer/predicted-arrival/coordination = synthetic simulator events over a selected configured link;
- observation provenance = AI/simulation/manual/unavailable source classification.

Do not silently convert one category into another.

## 8. Device-camera role

Camera nodes capture/upload frames and expose simple device status/settings. Heavy inference, model training, signal scenarios, analytics, network cooperation, and experiment logic stay on the PC side.

## 9. Capability and safety boundaries

See `PROJECT_SCOPE.md` for implemented/foundation/planned status. Multi-intersection cooperation and emergency priority require additional simulator/controller evidence. All signal phases/actions remain prototype/simulation outputs; public-road control is outside scope.

## V028 pedestrian-aware network layer

Inside `network_simulation_experiments.py`, V028 keeps four isolated benchmark modes. `pedestrian_aware_cooperative` reuses the same per-intersection controllers and V027 coordinator, while adding local pedestrian request-age and synthetic crossing state. A bounded guard can request earlier protected pedestrian service at the maximum-wait threshold or reserve additional WALK/CLEAR time for active synthetic crossings. Phase order and configured min/max/cycle limits remain controller-owned.
