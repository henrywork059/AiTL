# AI Agent Guide

Detailed operating guide for AI coding agents working on **AI Traffic Light (AiTL)**. `../AGENTS.md` is mandatory and takes priority. For routine patch execution, use `PATCH_PLAYBOOK.md`; this guide explains the architecture/decision rules behind it.

## 1. Mental model

AiTL has several deliberately separate paths.

### Shared live camera/inference path

```text
saved ESP sessions / built-in simulation
→ one selected CameraFrameService source
→ local inference
→ tracking + zones
→ occupancy / flow / zone-class observations
→ ranked simulated signal controller
→ explanation / analytics / UI
```

Several ESP sessions may run, but **one selected source** feeds the shared live AI/traffic pipeline.

### Junction topology/observability path

```text
config/intersections.json
→ IntersectionNetworkService
→ source/junction mapping + directed links + node layout

RemoteCameraManager health
+ selected CameraFrameService source
+ current traffic/decision state
→ JunctionNetworkOverviewService
→ Junction Network page
```

Junction topology, layout, multi-camera assignment and camera/live-status visualization are implemented. Simultaneous independent inference/controller pipelines for all junctions are **not** implemented. Only the junction resolved from the current shared source receives live traffic values.

### Data/model path

```text
capture + metadata
→ manual review/labels
→ managed YOLO dataset
→ local training
→ model registry
→ local inference
```

### Isolated experiment paths

Single-junction and network experiments use separate deterministic simulator/controller state and synthetic provenance. They do not mutate the live camera/controller runtime and do not create public-road authority.

## 2. Resolve authority before coding

Use `DOCUMENTATION_MAP.md`. When repository state matters:

1. owner's explicit current instruction;
2. current GitHub `main` source/tests/contracts;
3. root `VERSION` for release state;
4. `AGENTS.md` + `PROJECT_SCOPE.md` for mandatory boundaries;
5. current candidate docs;
6. durable guides;
7. historical docs.

Do not let a historical patch note or stale durable sentence override current code/`VERSION`.

## 3. Start with the short playbook

Before broad reading, use `PATCH_PLAYBOOK.md` to record:

```text
version/status/previous/baseline
same candidate or explicit new candidate
owning modules
contracts affected
focused regression
runtime data at risk
```

This avoids spending most of a patch rediscovering repository structure.

## 4. Version-state gate

### Unaccepted candidate

If `version != passed_baseline`, continue/repair/harden the same candidate unless the owner explicitly requests a new version.

### Explicit new candidate

Prepare the release bundle first and update root `VERSION` **last**, or commit the full bundle atomically when tooling permits. Do not create an inconsistent `main` where the new `VERSION` exists before its patch doc/changelog/current testing/frontend version surfaces.

### Acceptance

Only explicit owner acceptance changes `passed_baseline`. Tests/builds/main-branch presence do not imply acceptance.

## 5. Capability-claim gate

Before documenting a capability, classify it:

- **implemented** — working code path exists;
- **foundation** — supporting schema/service exists but target behavior is inactive;
- **simulation-only** — behavior is confined to simulator/test path;
- **planned** — no completed target behavior;
- **out of scope** — explicitly excluded.

Examples:

- several saved cameras = implemented multi-camera session/input support;
- several cameras assigned to a junction = implemented configuration/observability;
- one selected camera feeding AI = current live inference architecture;
- several configured links = topology metadata, not observed vehicle transfer;
- network experiment cooperation/emergency/class events = synthetic experiment evidence unless current live code explicitly implements otherwise.

## 6. Ownership rules

### Backend

- `routes/` — HTTP translation only;
- `services/` — domain behavior/state/filesystem/inference/training;
- `models.py` — Pydantic requests/contracts;
- `core/` — envelope/errors/logging/middleware/version/shared persistence.

Important owners:

- selected frame/simulation: `camera_frames.py`;
- one physical ESP session: `remote_camera.py`;
- saved multi-ESP registry/session arbitration: `remote_camera_manager.py`;
- junction/source/topology/layout: `intersection_network.py`;
- read-only Junction Network projection: `junction_network_overview.py`;
- signal arbitration: `signal_rules.py`;
- isolated single-junction experiments: `simulation_experiments.py`;
- isolated network experiments: `network_simulation_experiments.py`;
- pure network overlay priority selection: `network_policy_arbiter.py`;
- live explanation projection: `decision_context.py`;
- stored normalized network evidence: `decision_evidence.py`.

Do not create a second camera registry, intersection database, signal controller or evidence arbiter when an owner already exists.

### Frontend

- `App.tsx` — composition/top-level coordination only;
- `pages/` — page state/interaction;
- `components/` — reusable presentation;
- `lib/*Api.ts` / API layer — typed HTTP calls;
- `types/` — shared response/domain shapes;
- `constants/` — navigation/release/function catalog;
- `useSerialPolling` — non-overlapping periodic async refresh.

## 7. Low-risk implementation order

Use:

```text
domain/service behavior
→ focused regression
→ route/API/type wiring
→ frontend wiring
→ contract/scope/architecture docs
→ release bundle (only for explicit new version)
→ full owner runner
```

This keeps defects near the changed owner and avoids version/doc churn while code is still moving.

## 8. Regression rules

The normal runner automatically discovers zero-argument `scripts/test_*.py` files.

A good focused regression:

- exercises the semantic invariant directly;
- uses temporary paths/fakes instead of private runtime data;
- is deterministic;
- requires no user input;
- fails clearly with one cause;
- may add a small wiring/structure guard when a feature spans backend/frontend registration.

Do not accidentally name a hardware CLI that requires `--host`, Wi-Fi credentials, special firmware or manual interaction as an ordinary automatic regression unless the runner explicitly excludes it.

## 9. Data integrity and state review

Treat datasets, labels, runtime config, camera profiles, models, histories and experiment outputs as user data.

When state/persistence changes, review:

- old-config migration/defaults;
- source/session generation and stale cache behavior;
- atomic writes/locks;
- reset/delete/reassignment behavior;
- failure cleanup/restoration;
- polling vs unsaved edits;
- bounded histories/caches.

Never use destructive cleanup merely to make tests/pulls pass.

## 10. Semantics and provenance

Never conflate:

- occupancy with flow;
- per-frame zone/class counts with throughput;
- configured travel time with measured transfer;
- logical junction canvas position with geospatial/GPS location;
- simulation/manual evidence with AI detection;
- multiple camera sessions with simultaneous multi-camera inference.

Canonical detection boxes stay in original-image coordinates. Zone geometry stays in its validated reference coordinate system; display scaling is presentation-only.

## 11. Signal/network safety

Ranked scenarios remain bounded simulated policies. Preserve protected minimums, maximums, cycle limits, phase order, stale fallback, persistence/cooldown and incident recovery.

Network experiment overlays must not compete by call order. Keep pure arbitration ownership and explicit synthetic provenance. Do not relabel simulation emergency/class/cooperation evidence as live perception or public-road control.

## 12. API/error/logging

Use standard envelopes and central stable error codes. Binary/image/CSV responses retain `X-Request-ID`.

When HTTP/schema/error behavior changes, update the contract and focused regression in the same candidate. A route should normally be input validation → service call → envelope/logging.

## 13. Documentation synchronization

Use `DOCUMENTATION_MAP.md`.

For a new candidate, treat these as one release bundle:

```text
PATCH_<version>.md
CHANGELOG.md
START_HERE.md
LOCAL_TESTING.md
TEST_READY_CHECKLIST.md
frontend projectVersion.ts
VERSION (last)
```

Update durable architecture/function/scope docs only when their responsibility changed. If code changes a durable configuration (for example framebuffer mode), update the architecture text immediately so a future agent does not restore an obsolete design based on stale documentation.

## 14. Validation

Routine owner validation uses:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

It pulls, reloads itself, refreshes dependencies, compiles, runs structure + automatic regressions, typechecks/builds frontend, checks tracked-tree hygiene, safely restarts AiTL-owned processes, runs live smoke and opens PC Studio.

Use individual commands only to diagnose the failed stage. State clearly what actually ran in the agent environment and what still requires the owner's complete local repository/hardware.

## 15. Code-review questions before handoff

Ask:

- Is behavior in the correct owner?
- Did I create duplicate state/schema?
- Can source switching expose stale/wrong-source data?
- Can polling overlap or overwrite unsaved edits?
- Does failure restore prior state?
- Is persistence atomic/backward-compatible?
- Is the UI bounded/responsive for empty/long/error states?
- Is any magic threshold undocumented?
- Does the function/navigation registry reflect the implemented page?
- Do durable docs match actual production configuration?
- Does any capability sentence claim more than code/evidence supports?

## 16. Handoff

Keep the result evidence-based:

```text
Version decision
Implemented
Deliberately unchanged/not implemented
Automated checks actually run
Checks still required locally
Manual acceptance focus
Passed baseline
```

Never mark a candidate passed without explicit owner acceptance.
