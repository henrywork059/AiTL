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
- isolated deterministic Simulation Lab experiments;
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

Do not move signal arbitration into routes/network/explanation services. `services/signal_rules.py` owns ranked scenario arbitration and protected simulated timing. `services/simulation_experiments.py` owns isolated experiment runs. `services/intersection_network.py` owns topology/source identity. `services/decision_context.py` projects explanation context but does not control the signal.

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
- experiment telemetry = isolated synthetic simulator output;
- network links = configured topology metadata.

## Network/explanation foundation

The current foundation can persist generic intersections/links, resolve source IDs to intersection identity, and expose neighbour/decision context. It does **not** yet run simultaneous multi-intersection controllers, transfer vehicles between intersections, coordinate green phases, or implement emergency pre-emption.

Future network behavior should create explicit per-intersection runtime/controller state and transfer/arrival context while reusing the existing ranked-scenario controller.

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
