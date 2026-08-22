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

## 3. Network/explanation foundation and V031 experiment path

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

The current V031 benchmark keeps the isolated experiment path and layers bounded pedestrian, class, emergency, cooperation and evidence behavior over the protected controller:

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

`network_simulation_experiments.py` owns this isolated path. It creates separate controller instances, explicit synthetic transfer events, and simulation-only network policy overlays without touching live camera/controller runtime. `network_policy_arbiter.py` is a pure selector that chooses one overlay owner per intersection/tick; it never changes timing directly. Ranked scenarios are evaluated once as the controller-owned base policy, then post-advisory reads use a non-reapplying snapshot.

V031 overlay priority is explicit: **incident hold > active pedestrian crossing > simulated emergency priority > pedestrian max-wait > configured vehicle-class priority > network cooperation**. This removes call-order arbitration between the network overlays. Protected phase order and min/max/cycle bounds remain controller-owned.

The benchmark also gives protected-service requests a lifecycle (`service`, `source`, `priority`, `started_at_s`, satisfaction) so a status field is not mistaken for causal state after the requested service has begun.

### Current comparison / ablation modes

The seven modes remain separate comparison variants: Fixed, Independent Adaptive, Cooperative Adaptive, Pedestrian-aware Cooperative, Class-aware Cooperative, Emergency Baseline Cooperative, and Emergency-priority Cooperative. They are **not** one all-features-integrated controller. In particular, class-aware and emergency-priority overlays do not currently execute together in the same mode.

The network overlays do not replace `SignalRulesService`, do not reorder phases, and do not write a second physical signal policy. They may change only bounded simulated phase duration/progression through the benchmark controller. Active crossing protection outranks simulated emergency priority; simulated emergency priority outranks pedestrian max-wait, while every protected phase minimum/sequence remains enforced.

Live configured links remain **metadata**, not observed transfers. V027 transfer, predicted-arrival, and coordination events are synthetic simulator evidence. V029 emergency priority is likewise isolated synthetic experiment evidence, not live perception or hardware pre-emption.

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
- `network_simulation_experiments.py` — isolated current seven-mode two-intersection experiment, synthetic transfer and bounded simulation policy layers;
- `decision_evidence.py` — V031 normalized persistent network decision-evidence projection/export; no arbitration;
- `intersection_network.py` — intersection/source/topology metadata;
- `decision_context.py` — non-controlling structured live explanation.

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

See `PROJECT_SCOPE.md` for implemented/foundation/planned status. The selected two-intersection benchmark now has cooperation, pedestrian, class, emergency and V031 normalized explainability evidence. General N-intersection orchestration and live evidence still require additional architecture. All signal phases/actions remain prototype/simulation outputs; public-road control is outside scope.

## V028 pedestrian-aware network layer

Inside `network_simulation_experiments.py`, V028 keeps four isolated benchmark modes. `pedestrian_aware_cooperative` reuses the same per-intersection controllers and V027 coordinator, while adding local pedestrian request-age and synthetic crossing state. A bounded guard can request earlier protected pedestrian service at the maximum-wait threshold or reserve additional WALK/CLEAR time for active synthetic crossings. Phase order and configured min/max/cycle limits remain controller-owned.

## V029 emergency-priority network layer

V029 adds two matched modes to the existing isolated network experiment:

```text
seeded base demand + same configured emergency event
          |
          +--> Emergency Baseline Cooperative
          |      pedestrian-aware cooperation; emergency vehicle is ordinary demand
          |
          +--> Emergency-priority Cooperative
                 same controllers/demand/event
                 + source priority advisory
                 + downstream preparation from transfer ETA
                 + destination priority advisory
                 + protected crossing denial guard
                 + clear/recovery evidence
```

Emergency priority remains an advisory layer on the existing per-intersection `SignalRulesService` adapters. It does not create a parallel signal state machine. The controller remains owner of phase order, phase minimum/maximum durations, pending service requests, and maximum-cycle bounds.

The network simulation owns the configured event lifecycle and synthetic vehicle transfer. It determines whether the emergency vehicle is waiting at A, in the A→B pipeline, waiting at B, or cleared, then supplies role/ETA context to the relevant controller.

The priority layer is evaluated after pedestrian-awareness/cooperation advisories so emergency context can request the final bounded timing adjustment for that simulation step. It still cannot bypass protected limits; active simulated pedestrian crossing occupancy causes an explicit deny decision.

This architecture is deliberately separate from the live camera path. No V029 service maps camera detections to emergency events, and no V029 route sends pre-emption commands to physical signal hardware.

## V030 vehicle-class-aware experiment layer

The class-aware policy remains inside `app/services/network_simulation_experiments.py`; it does not create a parallel live controller. Synthetic regular classes are generated by deterministic arrival planning, normalized to the documented taxonomy, projected into existing zone/class observations, and aggregated into per-intersection/network class metrics. `class_aware_cooperative` reuses the same per-intersection signal controllers, cooperation and pedestrian guards, then optionally applies one bounded selected-class advisory. Emergency modes remain separate.

Dependency boundary: **synthetic class demand → existing queue/zone observations → class-aware experiment advisory → protected signal timing → structured class evidence**. No path from V030 synthetic class generation is connected to physical/public-road signal hardware or claimed as live detector accuracy.


## V031 persistent evidence layer

V031 adds a non-controlling projection service after all network modes finish:

```text
protected simulator modes
      |
      +--> detailed scenario / cooperation / pedestrian / class / emergency histories
                    |
                    +--> decision_evidence.py
                           |
                           +--> schema-v1 compact normalized ledger stored in new runs
                           +--> on-demand projection for older runs
                           +--> JSON evidence endpoint
                           +--> evidence CSV export
```

`decision_evidence.py` consumes completed result data only. It cannot call timing mutation methods, select winners, change phase state, or write live camera/controller state. `network_simulation_experiments.py` remains the owner of the experiment lifecycle and persists the resulting ledger alongside existing raw evidence.

V031 also captures scenario evidence snapshots in each simulated intersection when the active ranked winner changes for a protected phase. The capture happens **after** the controller returns its state and is read-only with respect to arbitration/timing. The snapshot provides the local observations needed by the normalized ledger for V031+ runs.

The normalized ledger is deliberately a compact projection with `source_ref` pointers. Detailed raw histories remain the drill-down source and backward-compatible contract. Older runs are never silently rewritten merely to add a V031 projection.
