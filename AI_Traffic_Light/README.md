# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light **simulation** prototype with a FastAPI backend and React/Vite PC Studio frontend.

## Current release state

Root [`VERSION`](VERSION) is authoritative. At this update, V030 / `0_3_0` is the current unaccepted candidate and V024 / `0_2_4` remains the owner-confirmed passed baseline. V029 is the previous version because the owner explicitly requested V030 before separately accepting V029. If this sentence ever disagrees with `VERSION`, follow `VERSION` and update this current-state summary.

V030 preserves the V029 emergency/cooperation/pedestrian stack and adds explicit regular vehicle classes, deterministic class-mix profiles, per-class telemetry, and a seventh Class-aware Cooperative mode. Class-aware timing is bounded, configurable, and explicitly synthetic; the V029 matched emergency pair remains separate.

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
| Current candidate acceptance | [`docs/PATCH_0_3_0.md`](docs/PATCH_0_3_0.md), [`docs/TEST_READY_CHECKLIST.md`](docs/TEST_READY_CHECKLIST.md) |
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
- seven-mode network evidence: Fixed, Independent Adaptive, Cooperative Adaptive, Pedestrian-aware Cooperative, Class-aware Cooperative, matched Emergency Baseline Cooperative, and Emergency-priority Cooperative;
- pedestrian request-age, synthetic crossing occupancy, starvation-prevention, service-session, and clearance-protection telemetry;
- bounded downstream coordination using predicted synthetic upstream arrivals with protected pedestrian/timing guards;
- explicit simulated emergency-event lifecycle, matched no-priority baseline, protected grant/deny/defer priority, downstream preparation, recovery, and emergency wait/travel telemetry;
- regular synthetic class taxonomy, deterministic class profiles, per-class arrival/service/wait/queue evidence, and bounded configurable class-priority events;
- structured live decision/explanation **foundation** with observation provenance.

## Important semantics

- Occupancy is sampled presence, not throughput.
- Flow is produced by prototype track/line/region events.
- Zone/class counts are per-frame observations.
- Simulation Lab data is synthetic experiment output, separate from live histories.
- Live network links remain configuration metadata; V030 cooperation, pedestrian-aware service guards, class-aware behavior, and emergency priority exist only inside the isolated synthetic network experiment. Transfer/predicted-arrival/class/emergency evidence is simulator-generated, not observed real traffic or live recognition.
- Manual/synthetic events must remain labeled with their provenance.

## Planned invention capability areas

The project scope explicitly includes:

1. multi-intersection cooperation (two-intersection synthetic implementation, broader generalization planned);
2. emergency priority (V029 synthetic/configured implementation, live evidence planned);
3. pedestrian-aware control (V028 synthetic implementation, live-evidence strengthening planned);
4. different vehicle classes (V030 synthetic class-aware implementation, live-evidence strengthening planned);
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

AiTL is for local simulation, classroom/model-junction work, computer-vision experiments, and supervised testing. Detections, analytics, scenario decisions, class/emergency priorities, timings, topology, explanations, and experiment results are **not connected to physical/public-road traffic infrastructure**. Production/public-road autonomous control is outside project scope.
