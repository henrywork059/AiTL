# AI Agent Guide

Detailed operating guide for AI coding agents working on **AI Traffic Light (AiTL)**. `../AGENTS.md` is mandatory and takes priority when instructions overlap.

## 1. Mental model

AiTL is a local prototype with several deliberately separate data/control paths:

```text
camera/upload/simulation frame
→ local inference
→ tracking + zones
→ occupancy / flow / zone-class observations
→ ranked simulated signal controller
→ PC Studio explanation/visualization
```

```text
configured intersection/source identity + neighbour links
→ network context
→ decision explanation context
```

The second path is currently a **foundation**: topology/context does not itself create multi-intersection cooperation.

Data/model workflow:

```text
capture + metadata
→ manual review/labels
→ managed YOLO dataset
→ local training
→ model registry
→ local inference
```

Isolated experiment workflow:

```text
saved signal profile + zone snapshot + density/seed
→ separate Fixed simulator/controller
→ separate Adaptive simulator/controller
→ aligned synthetic telemetry
```

No path converts these outputs into public-road signal commands.

## 2. Resolve authority before coding

Use `DOCUMENTATION_MAP.md`. For repository state:

1. owner's explicit current instruction;
2. current GitHub `main` source/tests/contracts;
3. root `VERSION`;
4. `AGENTS.md` + `PROJECT_SCOPE.md`;
5. current candidate docs;
6. durable guides;
7. historical docs.

If a durable guide contains an obsolete current-version claim, do not follow the stale claim. Fix the durable guide when that is within patch scope.

## 3. Version-state decision gate

Read all `VERSION` fields before editing.

### `version != passed_baseline`

Current version is an unaccepted candidate unless the owner explicitly says otherwise. Repair/harden the same candidate by default.

### Owner explicitly confirms acceptance

Promote `passed_baseline` only in a repository update that records that explicit decision. Normal next-version work may then proceed from the accepted state unless the owner directs otherwise.

Never infer acceptance from unit tests, builds, upload to `main`, a test-ready label, or agent judgment.

## 4. Capability-claim gate

Before documenting a capability, classify it using `PROJECT_SCOPE.md`:

- implemented;
- foundation;
- simulation-only;
- planned;
- out of scope.

A schema, toggle, source ID, configured link, class label, or placeholder does not prove the target behavior is implemented. For example, a neighbour link is topology metadata until a real multi-intersection simulator/controller uses neighbour information to alter a bounded decision.

## 5. Preflight inspection

For a non-trivial patch inspect, as relevant:

```text
VERSION
AGENTS.md
DOCUMENTATION_MAP.md
PROJECT_SCOPE.md
relevant source + tests
API_CONTRACTS.md
ERROR_CODES.md / error_codes.py
DATA_FORMAT.md / schemas
ARCHITECTURE.md / CODE_STRUCTURE.md
LOCAL_TESTING.md
TEST_READY_CHECKLIST.md
PATCH_<version>.md
```

Inspect nearby modules before adding a new abstraction. Reuse existing services/types/helpers when ownership already matches.

## 6. Change-size decision rules

Prefer the smallest cohesive change. Refactor when duplication or ownership ambiguity materially blocks the request, not merely because a file is long.

For planned network features, extend the current ranked-scenario/controller architecture rather than creating a separate "smart" controller. Establish identity/state/transfer evidence before cooperation algorithms. Do not hard-code exactly two intersections into generic services.

## 7. Backend implementation protocol

### Routes

Routes translate HTTP input/output only:

- Pydantic input where applicable;
- service call;
- standard envelope or binary response;
- request ID;
- logging at the appropriate boundary.

Do not place filesystem, topology validation, arbitration, training, or inference algorithms in routes.

### Services

Services own domain behavior/side effects. Important ownership includes:

- camera state: `camera_frames.py`;
- detection/inference: inference service;
- zones/occupancy: zones + traffic history;
- tracking/flow: tracking + traffic flow;
- signal arbitration: `signal_rules.py`;
- isolated A/B simulation: `simulation_experiments.py`;
- intersection/topology identity: `intersection_network.py`;
- non-controlling explanation projection: `decision_context.py`.

### Core

Cross-cutting envelopes, stable errors, request middleware, logging, root-version metadata, and shared atomic JSON primitives belong in `app/core/`.

## 8. Frontend implementation protocol

Keep page behavior in pages, reusable rendering in components, HTTP logic in the API layer, and shared response shapes in TypeScript types.

For overlays, persist canonical image/reference coordinates and scale only for display. For dense analytics/experiments/explanations, use tabs/panels/details/dropdowns/filtering/internal scrolling rather than an unbounded dashboard.

Periodic async polling must not overlap. Prefer the shared serial scheduler or an equivalent self-scheduling pattern.

## 9. Data-integrity and semantics protocol

Treat datasets, labels, runtime config, models, histories, and experiment outputs as user data.

Never conflate:

- occupancy with flow;
- a zone/class per-frame count with throughput;
- configured travel time with measured arrival time;
- Simulation Lab data with live histories;
- manual/synthetic events with AI detections.

When changing deletion/build/persistence logic, define paired files, failure behavior, locks, stale markers, and stable error paths.

## 10. Signal and network safety protocol

Ranked scenarios may alter bounded **simulated** phase timing or request protected service sooner. Preserve protected minimums, maximums, cycle limits, phase sequence, stale fallback, persistence/cooldown, and incident recovery.

For future multi-intersection cooperation:

- use per-intersection controller/runtime state;
- use explicit transfer/arrival events or predictions;
- retain deterministic protected local safety bounds;
- record which neighbour context changed a decision;
- compare cooperative against independent control in the same seeded demand scenario.

For emergency priority, begin with simulation/configured events unless a compatible detector is intentionally introduced. Record event lifecycle and recovery. Do not equate an arbitrary class label with validated emergency recognition.

## 11. API/error/logging protocol

Use the standard envelopes and central stable error codes. Do not invent one-off route error JSON. Binary/image/CSV responses retain `X-Request-ID`.

When endpoints/schemas/errors change, update contract docs and focused tests in the same patch.

## 12. Testing protocol

Use the backend `.venv` when available. Typical validation:

```powershell
python -m compileall .\apps\pc-studio\backend\app .\scripts
python .\scripts\check_structure.py
```

Then run focused and inherited regressions relevant to the changed ownership. Run live `test_backend_smoke.py` with the backend active when practical.

Frontend:

```powershell
npm ci
npm run typecheck
npm run build
```

Repository/handoff hygiene:

```text
git diff --check
version-surface check
runtime/generated-file exclusion scan
patch ZIP validation
manifest comparison
SHA-256
```

State clearly what did and did not run.

## 13. Documentation synchronization protocol

Follow `DOCUMENTATION_MAP.md` instead of mechanically editing every document.

Long-lived guides should describe rules without hard-coded current release state. Current candidate details belong in `VERSION`, `START_HERE`, current `PATCH_*`, `LOCAL_TESTING`, and `TEST_READY_CHECKLIST`.

When planned scope changes, update `PROJECT_SCOPE.md` and `ROADMAP.md`. When architecture ownership changes, update `ARCHITECTURE.md` and `CODE_STRUCTURE.md`. When the API/data/error contract changes, update its dedicated contract.

## 14. Patch assembly protocol

Build from an explicit changed-file manifest, not the project root. Every archive member begins with `AI_Traffic_Light/`. Exclude runtime/generated content. Validate archive integrity and compare members to the intended manifest.

## 15. Handoff protocol

Tell the owner exactly:

- candidate/version decision;
- files changed;
- implemented vs foundation/planned changes;
- limitations;
- checks actually run;
- checks still required locally;
- acceptance steps;
- archive/manifest hash.

Do not mark a passed baseline until explicit owner acceptance.

## 16. Common failure patterns

- using a stale durable guide as release truth;
- silently starting a new version while a candidate is unaccepted;
- claiming configured topology as active cooperation;
- claiming a detector class/manual flag as a validated perception capability;
- putting service logic in routes;
- duplicating controller/arbitration logic in a network module;
- growing `App.tsx` into a domain container;
- summing occupancy into throughput;
- losing provenance between AI/simulation/manual observations;
- destructive cleanup of runtime/user data;
- full-repository patch ZIPs;
- reporting unrun tests as passed;
- rewriting historical version facts during documentation cleanup.
