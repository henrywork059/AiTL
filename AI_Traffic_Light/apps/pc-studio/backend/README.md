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
- structured non-controlling live decision context.

See `../../../docs/PC_STUDIO_FUNCTION_LIST.md` for the current function catalog and `../../../docs/PROJECT_SCOPE.md` for implemented/foundation/planned capability status.

## Architecture ownership

```text
app/main.py       FastAPI creation/wiring only
app/routes/       HTTP translation
app/services/     domain behavior/state/persistence/inference/training
app/models.py     Pydantic contracts
app/core/         envelopes/errors/logging/middleware/version/persistence helpers
```

Do not move signal arbitration into routes/network/explanation services. `services/signal_rules.py` owns ranked scenario arbitration and protected simulated timing. `services/simulation_experiments.py` owns isolated single-junction experiments. `services/network_simulation_experiments.py` owns isolated V027 Fixed / Independent Adaptive / Cooperative Adaptive two-intersection experiments and the simulation-only bounded coordinator. `services/intersection_network.py` owns topology/source identity. `services/decision_context.py` projects explanation context but does not control the signal.

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
- live network links = configured topology metadata; V027 transfer/predicted-arrival/coordination events exist only inside the isolated network experiment.

## Network simulation / explanation

The live/runtime foundation can persist generic intersections/links, resolve source IDs to intersection identity, and expose neighbour/decision context. Live camera processing still uses the existing single active traffic/controller path.

V027 keeps the isolated two-intersection experiment and runs three modes from the same seeded demand: Fixed, Independent Adaptive, and Cooperative Adaptive. Cooperative mode uses predicted synthetic arrivals already in the A→B transfer pipeline to issue bounded timing advisories to the downstream simulation controller. It may extend vehicle green within saved phase/cycle caps or request earlier protected progression; it does not shorten pedestrian WALK/CLEAR while local pedestrian demand is active.

This cooperation is simulation-only and does not mutate live camera/controller runtime. Emergency priority/pre-emption remains unimplemented.

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
