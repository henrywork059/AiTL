# AGENTS.md — mandatory rules for AiTL coding agents

This is the mandatory repository instruction for any AI coding agent, assistant, or automation working inside `AI_Traffic_Light/`.

## 1. Fast read order

Do **not** reread the entire documentation set for every small patch.

Start with:

1. `VERSION` — authoritative candidate/status/previous/passed baseline.
2. `AGENTS.md` — these mandatory rules.
3. `docs/PATCH_PLAYBOOK.md` — short implementation/release/test sequence.
4. affected source + focused tests + task-specific contract.

Then open as needed:

- `docs/DOCUMENTATION_MAP.md` — document authority/update ownership;
- `docs/PROJECT_SCOPE.md` — capability/evidence boundaries;
- `docs/AI_AGENT_GUIDE.md` — detailed architecture/development rationale;
- current `PATCH_*`, `LOCAL_TESTING`, `TEST_READY_CHECKLIST` — candidate-specific testing/acceptance.

When repository state matters, inspect current GitHub `main`. Never substitute a conversation summary, old local snapshot, historical patch note, or remembered version for current repository evidence.

## 2. Release-state gate

`VERSION` is the only release-state authority and must contain:

```text
version
status
previous_version
passed_baseline
notes
```

Rules:

- `version != passed_baseline` means the current version is unaccepted unless the owner explicitly says otherwise.
- Continue/fix/review/harden an unaccepted candidate as the **same candidate** by default.
- Increment patch `Z` only when the owner explicitly requests the next patch/version.
- Never promote a candidate because tests/builds pass or because code is on `main`.
- Change `passed_baseline` only after explicit owner acceptance.

### New-version release-bundle rule

For an explicitly requested new candidate, prepare these first:

```text
docs/PATCH_<version>.md
CHANGELOG.md
docs/START_HERE.md
docs/LOCAL_TESTING.md
docs/TEST_READY_CHECKLIST.md
apps/pc-studio/frontend/src/constants/projectVersion.ts
```

Then update root `VERSION` **last**, or commit the release bundle atomically when tooling permits. Do not create a `main` state where `VERSION` points to missing/stale release surfaces.

## 3. Safety/capability boundary

AiTL is a local/student-scale computer-vision and traffic-light simulation prototype.

Do not implement, document, or imply:

- direct public-road signal control;
- traffic-cabinet/controller integration;
- bypassing signal safety interlocks;
- certified/production autonomous authority;
- perception capability unsupported by the active detector/source.

Use exact status words: **implemented**, **foundation**, **simulation-only**, **planned**, **out of scope**.

Multiple saved/streaming cameras and multiple junction assignments do **not** imply simultaneous multi-camera/multi-junction inference. A configured topology link does **not** prove observed vehicle transfer or live cooperation. Synthetic/manual evidence must stay labeled synthetic/manual.

## 4. Architecture ownership

### Backend

```text
app/main.py       wiring/middleware/handlers only
app/routes/       HTTP translation only
app/services/     business/state/filesystem/inference/training logic
app/models.py     Pydantic request contracts
app/core/         envelopes/errors/logging/middleware/version/shared persistence
```

Important owners:

- selected frame/simulation — `camera_frames.py`;
- one physical ESP session/transport — `remote_camera.py`;
- saved multi-ESP registry/session arbitration — `remote_camera_manager.py`;
- junction/source/topology/layout — `intersection_network.py`;
- read-only Junction Network projection — `junction_network_overview.py`;
- protected simulated signal arbitration — `signal_rules.py`;
- isolated network benchmark — `network_simulation_experiments.py`;
- pure network overlay priority selection — `network_policy_arbiter.py`;
- live explanation projection — `decision_context.py`;
- stored normalized network evidence — `decision_evidence.py`.

Do not create a parallel controller, camera registry, intersection database, or evidence arbiter.

### Frontend

```text
src/App.tsx       composition/top-level coordination
src/pages/        page behavior/state
src/components/   reusable presentation
src/lib/*Api.ts   typed feature HTTP calls
src/lib/apiClient.ts envelope/error handling
src/lib/useSerialPolling.ts non-overlapping periodic async work
src/types*/       shared API/domain types
src/constants/    navigation/version/function catalog
```

Do not turn `App.tsx` into page-specific business logic. Keep high-frequency polling serial/non-overlapping.

## 5. Data/semantics invariants

Preserve unless the task explicitly changes them:

- **occupancy** = sampled presence;
- **flow** = track-derived line/region events;
- **zone/class counts** = per-frame detector observations;
- **experiment telemetry** = isolated synthetic output;
- **network links** = configured topology metadata in live state;
- **junction node position** = logical UI layout, not GPS;
- **observation provenance** = explicit AI/simulation/manual/unavailable source.

Canonical boxes remain original-image coordinates. Zone geometry remains in its validated reference coordinate system.

The shared live pipeline currently has one selected `CameraFrameService` source. Do not copy its live occupancy/decision data onto unobserved junctions.

## 6. API/error/logging contract

JSON success:

```json
{"ok": true, "data": {}, "meta": {"request_id": "..."}}
```

JSON error:

```json
{"ok": false, "error": {"code": "...", "message": "...", "details": {}}, "meta": {"request_id": "..."}}
```

Binary/image/CSV responses preserve `X-Request-ID`.

When HTTP/schema behavior changes, update `docs/API_CONTRACTS.md` and focused tests. When stable errors change, synchronize `error_codes.py` and `docs/ERROR_CODES.md`.

## 7. Runtime/user data is not patch content

Never use destructive cleanup such as `git clean -fd`. Preserve:

```text
datasets/
outputs/
*.pt
manual labels
config/remote_cameras.json
config/zones.json
config/runtime_settings.json
config/signal_rules.json
config/intersections.json
.venv/
node_modules/
dist/
caches
```

Patch archives/source commits must not add generated/runtime data.

## 8. Low-risk implementation order

For non-trivial work:

1. resolve release state;
2. identify the smallest owner module;
3. inspect existing focused regression/contract;
4. implement domain/service behavior;
5. add/update a focused deterministic regression;
6. add route/API/type/frontend wiring only as required;
7. update only affected contract/scope/architecture/function docs;
8. synchronize release bundle only if a new candidate was explicitly requested;
9. hand off to the normal owner runner.

Prefer extension of existing services/data models over parallel abstractions.

## 9. Regression rule

`scripts/update_test_run.ps1` auto-discovers zero-argument `scripts/test_*.py` regressions.

Therefore:

- ordinary offline regressions should be deterministic zero-argument `test_*.py` files;
- test the semantic invariant, not only file/string presence;
- add a small wiring guard when several files/registries must stay connected;
- hardware/interactive utilities requiring `--host`, credentials, special firmware or user input must not accidentally become ordinary automatic regressions unless explicitly excluded/documented by the runner.

## 10. Validation evidence must be precise

Normal owner validation:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

It updates, reloads itself, installs/refreshes dependencies, compiles, runs structure + auto-discovered regressions, typechecks/builds frontend, checks tracked-tree cleanliness, safely restarts only AiTL-owned PC Studio processes, runs live smoke, and opens PC Studio.

Use individual commands only to diagnose a failed stage.

Agent handoff must separate:

- checks actually run in the current environment;
- targeted/static review evidence;
- checks still required on the owner's complete local repository/hardware.

Never describe an unrun check as passed.

## 11. Documentation policy

Use `docs/DOCUMENTATION_MAP.md`.

- Keep durable guides version-agnostic.
- Put current candidate detail in release-bundle/current-testing docs.
- Fix durable architecture/ownership text in the same candidate when code makes it stale.
- Do not rewrite historical patch/changelog facts to make them current.
- Keep limitations adjacent to capability claims.

## 12. Code-review gate before handoff

Review changed code for:

- ownership violations/duplicate state;
- stale/wrong-source data after switching;
- overlapping polling;
- missing state restoration/cleanup (`finally` where appropriate);
- persistent writes bypassing atomic helpers;
- backward config/data compatibility;
- unbounded histories/UI growth;
- undocumented magic thresholds;
- reset/delete/reassignment edge cases;
- missing navigation/function/API registration;
- docs stronger or older than implementation.

For visual editors, also review narrow screens, long identifiers, empty/default states, unsaved edits during live polling, and persistence round-trip.

## 13. Network policy/evidence invariants

In isolated network experiments, ranked scenarios remain controller-owned base policy. Higher-level network overlays use one explicit owner per intersection/tick; they must not compete through call order. Preserve the documented priority order and non-reapplying snapshot semantics in `network_policy_arbiter.py` / network experiment tests.

Normalized `decision_evidence` remains an additive projection over detailed histories; it must not become an arbitration/timing owner and must preserve deterministic IDs/provenance/backward projection.

Vehicle-class/emergency/cooperation evidence remains synthetic experiment evidence unless a later explicit live implementation provides and tests real provenance.

## 14. Handoff/acceptance

Keep handoff concise:

```text
Version decision
Implemented
Deliberately unchanged/not implemented
Checks actually run
Checks still required locally
Manual acceptance focus
Passed baseline
```

The owner alone promotes a candidate. After explicit acceptance, update repository `passed_baseline` before normal next-version development; an immutable accepted tag may also be created when the owner's Git workflow permits it.
