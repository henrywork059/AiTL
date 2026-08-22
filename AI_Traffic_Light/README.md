# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light **simulation** prototype with a FastAPI backend and React/Vite PC Studio frontend.

## Current release state

Root [`VERSION`](VERSION) is authoritative. At this update, V027 / `0_2_7` is the current unaccepted candidate and V024 / `0_2_4` remains the owner-confirmed passed baseline. V026 is the previous version because the owner explicitly requested V027 before separately accepting V026. If this sentence ever disagrees with `VERSION`, follow `VERSION` and update this current-state summary.

V027 builds on V026 with a third Cooperative Adaptive network mode. Downstream timing can use predicted synthetic upstream arrivals for bounded, protected timing advisories, allowing Fixed vs Independent Adaptive vs Cooperative Adaptive comparison under the same seeded demand.

## Documentation entry points

| Need | Read |
| --- | --- |
| What is current? | `VERSION`, [`docs/START_HERE.md`](docs/START_HERE.md) |
| Which document is authoritative? | [`docs/DOCUMENTATION_MAP.md`](docs/DOCUMENTATION_MAP.md) |
| What is implemented vs planned? | [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) |
| AI/coding-agent rules | [`AGENTS.md`](AGENTS.md), [`docs/AI_AGENT_GUIDE.md`](docs/AI_AGENT_GUIDE.md) |
| Human update/test workflow | [`docs/HUMAN_GUIDE.md`](docs/HUMAN_GUIDE.md), [`docs/LOCAL_TESTING.md`](docs/LOCAL_TESTING.md) |
| Architecture/module ownership | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/CODE_STRUCTURE.md`](docs/CODE_STRUCTURE.md) |
| API/errors/data semantics | [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md), [`docs/ERROR_CODES.md`](docs/ERROR_CODES.md), [`docs/DATA_FORMAT.md`](docs/DATA_FORMAT.md) |
| Current candidate acceptance | [`docs/PATCH_0_2_7.md`](docs/PATCH_0_2_7.md), [`docs/TEST_READY_CHECKLIST.md`](docs/TEST_READY_CHECKLIST.md) |
| What comes next? | [`docs/ROADMAP.md`](docs/ROADMAP.md) |

## Implemented prototype functions

- receive/simulate camera frames;
- local trained-model inference;
- dataset capture/delete/review/manual labeling and managed YOLO training;
- model registry/load/default/delete;
- camera-aligned traffic zones and counting lines;
- sampled occupancy + lightweight track-derived flow analytics;
- configurable protected simulated signal timing;
- ranked adaptive scenarios using controller metrics or zone/class counts;
- deterministic one-winner arbitration with bounded timing/protected phase order;
- persistent signal decision history;
- isolated seeded Fixed-vs-Adaptive Simulation Lab with wait/queue/throughput/signal/scenario telemetry;
- persistent experiment results and CSV export;
- generic intersection/source identity and directed neighbour-link configuration;
- deterministic two-intersection network experiments with synthetic configured-link vehicle transfer;
- Fixed vs Independent Adaptive vs Cooperative Adaptive network comparison;
- bounded downstream coordination using predicted synthetic upstream arrivals with protected pedestrian/timing guards;
- structured live decision/explanation **foundation** with observation provenance.

## Important semantics

- Occupancy is sampled presence, not throughput.
- Flow is produced by prototype track/line/region events.
- Zone/class counts are per-frame observations.
- Simulation Lab data is synthetic experiment output, separate from live histories.
- Live network links remain configuration metadata; V027 cooperation exists only inside the isolated synthetic network experiment. Transfer and predicted-arrival evidence are simulator-generated, not observed real traffic.
- Manual/synthetic events must remain labeled with their provenance.

## Planned invention capability areas

The project scope explicitly includes:

1. multi-intersection cooperation;
2. emergency priority;
3. stronger pedestrian-aware control;
4. different vehicle classes;
5. explainable decisions.

Their completion levels differ. See [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) before making capability claims and [`docs/ROADMAP.md`](docs/ROADMAP.md) for dependency order.

## Development workflow

The project uses incremental changed-files-only patches. An unaccepted candidate is normally repaired as the same candidate; automated tests never promote the passed baseline. Only explicit owner acceptance changes `passed_baseline`.

Useful validation helpers:

```powershell
python .\scripts\check_structure.py
python .\scripts\validate_patch_zip.py <patch.zip>
```

See [`docs/DEVELOPMENT_WORKFLOW.md`](docs/DEVELOPMENT_WORKFLOW.md) for the full process.

## Safety scope

AiTL is for local simulation, classroom/model-junction work, computer-vision experiments, and supervised testing. Detections, analytics, scenario decisions, timings, topology, explanations, and experiment results are **not connected to physical/public-road traffic infrastructure**. Production/public-road autonomous control is outside project scope.
