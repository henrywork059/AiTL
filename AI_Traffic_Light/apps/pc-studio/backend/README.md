# PC Studio Backend

FastAPI backend for the local AiTL computer-vision and traffic-light simulation prototype. Root `AI_Traffic_Light/VERSION` is the release-state authority.

## Main responsibilities

- receive/store the latest device frame and run the synthetic signal-aware camera;
- dataset capture/delete/label/build workflow;
- local Ultralytics training/model registry/live inference;
- camera-aligned zones and sampled occupancy;
- lightweight cross-frame tracking and flow events;
- ranked simulated signal scenarios and protected phase timing;
- signal decision history/preview/Test inputs;
- isolated deterministic single-junction Simulation Lab experiments;
- isolated deterministic two-intersection network experiments with synthetic A→B transfer and bounded Cooperative Adaptive timing;
- runtime settings/logging;
- generic intersection/source/topology foundation;
- structured non-controlling live decision context;
- persistent normalized network decision-evidence projection and JSON/CSV evidence export.

See `../../../docs/PC_STUDIO_FUNCTION_LIST.md` for the current function catalog and `../../../docs/PROJECT_SCOPE.md` for implemented/foundation/planned capability status.

## Architecture ownership

```text
app/main.py       FastAPI creation/wiring only
app/routes/       HTTP translation
app/services/     domain behavior/state/persistence/inference/training
app/models.py     Pydantic contracts
app/core/         envelopes/errors/logging/middleware/version/persistence helpers
```

Do not move signal arbitration into routes/network/explanation services. `services/signal_rules.py` owns ranked scenario arbitration and protected simulated timing. `services/simulation_experiments.py` owns isolated single-junction experiments. `services/network_simulation_experiments.py` owns the current seven-mode isolated two-intersection experiment, synthetic transfer, and bounded cooperation/pedestrian/class/emergency policy layers. `services/intersection_network.py` owns topology/source identity. `services/decision_context.py` projects live explanation context but does not control the signal. `services/decision_evidence.py` normalizes stored network experiment evidence and exports it; it also never controls signal timing.

## API conventions

Successful JSON:

```json
{"ok": true, "data": {}, "meta": {"request_id": "..."}}
```

Expected errors use central stable error codes/AppError and the standard error envelope. Binary/image/CSV responses preserve `X-Request-ID`.

See `../../../docs/API_CONTRACTS.md` and `../../../docs/ERROR_CODES.md`.

## Data/persistence rules

Runtime/user data such as captures, labels, models, zone/settings/signal/network config, occupancy/flow/signal histories, and Simulation Lab results must not be included in changed-files source patches.

Replace-style runtime JSON persistence should use the shared atomic helper where the owning service's persistence semantics match it; services retain validation, locking, logging, and stable error translation.

Important semantic distinctions:

- occupancy = sampled presence;
- flow = track-derived events;
- zone/class counts = per-frame scenario observations;
- single-junction experiment telemetry = isolated synthetic simulator output;
- network-experiment telemetry = isolated synthetic two-intersection output;
- live network links = configured topology metadata; transfer/predicted-arrival/coordination/pedestrian/class/emergency evidence exists only inside the isolated network experiment.

## Network simulation / explanation

The live/runtime foundation can persist generic intersections/links, resolve source IDs to intersection identity, and expose neighbour/decision context. Live camera processing still uses the existing single active traffic/controller path.

The isolated two-intersection experiment now retains seven V030 comparison modes over the same seeded demand families. Cooperative/pedestrian/class/emergency policy layers remain bounded by the existing protected controller and do not mutate live camera/controller runtime. V031 adds only normalized evidence projection/export; it does not add another control mode.

## Local backend run

Typical Windows environment:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Use `../../../docs/LOCAL_TESTING.md` for current candidate validation. Do not describe a test as passed unless it actually ran.

## Safety boundary

The backend produces local prototype detection, analytics, scenario, experiment, topology, and explanation data. It is not a public-road traffic controller and does not connect its decisions to physical/public-road traffic infrastructure.

## V028 pedestrian-aware network evidence

The isolated network experiment now adds `pedestrian_aware_cooperative` beside Fixed, Adaptive and Cooperative. It tracks request age, service sessions, synthetic crossing occupancy and bounded starvation/clearance guards. These are simulator-only behaviors and do not change the live public-road safety boundary.

## V029 emergency-priority network evidence

`POST /api/traffic/network-experiments` now also produces matched `emergency_baseline_cooperative` and `emergency_priority_cooperative` results. The emergency event is a configured simulator input with explicit provenance, no detector claim, and lifecycle records. Priority remains bounded by the existing protected phase controller and active simulated pedestrian crossings can deny an emergency timing change. This feature does not connect to hardware pre-emption or public-road infrastructure.

## V030 vehicle-class-aware network evidence

`POST /api/traffic/network-experiments` now generates class-rich seeded regular traffic using `legacy`, `mixed_urban`, or `freight_heavy` profiles and adds `class_aware_cooperative`. Per-class arrival/transfer/service/wait/queue metrics and class-priority events use explicit `synthetic_vehicle_class_demand` provenance. The selected class weight is configurable; weight `1.0` is neutral, and any timing action remains inside the existing protected phase/cycle bounds with active pedestrian WALK/CLEAR protection. This is simulator evidence, not live detector accuracy or public-road transit/freight priority.


## V031 persistent decision evidence

Every new network experiment stores a `decision_evidence` schema-v1 projection while preserving the detailed scenario/cooperation/pedestrian/class/emergency histories. `GET /api/traffic/network-experiments/{run_id}/evidence` returns the normalized ledger and `/evidence.csv` exports it with `X-Request-ID`. Older stored runs without the V031 block are projected on demand and are not silently rewritten.
