# Start Here — current V026 candidate

Read root `VERSION` first. At this documentation update, V026 / `0_2_6` is the current unaccepted candidate. V025 / `0_2_5` is the previous version, and V024 / `0_2_4` remains the owner-confirmed passed baseline because the owner explicitly requested V026 before separately accepting V025.

## What V026 adds

### Deterministic two-intersection network experiment

V026 turns the V025 topology foundation into an actual isolated two-intersection simulation baseline:

- select one enabled directed network link;
- model its configured upstream and downstream intersections simultaneously;
- create a separate signal-controller runtime for each intersection;
- generate one deterministic exogenous vehicle/pedestrian arrival plan from density + seed and store a compact count/fingerprint snapshot;
- supply the same exogenous plan to Fixed and Adaptive network runs;
- discharge vehicles from the upstream queue according to that intersection's simulated signal state;
- move configured transfer candidates through a synthetic travel pipeline;
- deliver them to the downstream queue after the link's configured `travel_time_seconds`;
- retain per-vehicle transfer evidence with departure/scheduled-arrival/arrival time;
- calculate per-intersection and network aggregate telemetry;
- persist/list/reopen/delete/export network experiment results.

This is intentionally an **independent-controller baseline**. V026 does not feed neighbour arrival context into either controller, so `cooperative_control_active` remains false.

## New API surface

- `POST /api/traffic/network-experiments`
- `GET /api/traffic/network-experiments`
- `GET /api/traffic/network-experiments/{run_id}`
- `GET /api/traffic/network-experiments/{run_id}/export.csv`
- `DELETE /api/traffic/network-experiments/{run_id}`

The existing `/api/traffic/experiments` single-junction Fixed-vs-Adaptive benchmark remains unchanged.

## V025 capabilities retained

V026 keeps the V025 ranked scenario engine, protected phase/timing guards, single-junction Simulation Lab, intersection/source/topology configuration, observation provenance, and structured live decision context.

It also retains all earlier camera, inference, zones, occupancy, flow, dataset, training, model, settings, logging, and patch-safety behavior.

## Important V026 interpretation rules

- Network transfer events are **synthetic simulator events**, not observed live vehicle movement.
- Configured link travel time is a deterministic experiment input, not a learned/predicted road travel time.
- Fixed and Adaptive share exogenous demand, but policy-dependent upstream discharge can change downstream transfer-arrival timing; that difference is an experiment outcome.
- A transfer pipeline does not mean cooperation. Cooperation requires neighbour-informed controller decisions.
- The current PC Studio Simulation Lab UI remains the single-junction experiment view; V026 network experiments are API/test-first.
- Emergency priority remains inactive.

## Planned next dependency

The next logical capability is bounded **multi-intersection cooperation** using predicted/scheduled incoming demand from the now-testable transfer pipeline. That later work should compare:

1. Fixed;
2. Independent Adaptive;
3. Cooperative Adaptive.

The cooperation decision must remain integrated with the ranked scenario/protected phase architecture and record the neighbour evidence used.

## Recommended validation order

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
& $py ".\scripts\test_network_simulation_experiments.py"
```

Then run the full inherited backend regression set, live backend smoke, and frontend `npm ci`, `npm run typecheck`, `npm run build` as described in `LOCAL_TESTING.md`.

## Safety boundary

AiTL remains a supervised local simulation/computer-vision prototype. V026 network transfer, queues, timings, and metrics are synthetic experiment data and are not connected to physical/public-road signal infrastructure.
