# Development Workflow

This is the durable incremental workflow for AiTL. It intentionally does not hard-code the current candidate; root `VERSION` is authoritative. For the shortest execution path, use `PATCH_PLAYBOOK.md`.

## 1. Establish repository state

When the task depends on repository state, inspect current GitHub `main`. Then read the minimum authority set:

```text
VERSION
AGENTS.md
docs/DOCUMENTATION_MAP.md
docs/PROJECT_SCOPE.md
docs/PATCH_PLAYBOOK.md
```

Open the longer agent/architecture/contract guides only when the task touches those responsibilities.

Record before editing:

```text
version
status
previous_version
passed_baseline
requested new version? yes/no
owning modules
contracts affected
focused regression
```

This small preflight prevents most version, ownership and test-selection mistakes.

## 2. Apply the candidate gate

- If `version != passed_baseline`, the current release is unaccepted unless the owner explicitly says otherwise.
- A request to continue/fix/review/harden an unaccepted candidate stays on the same candidate.
- Increment `Z` only when the owner explicitly requests the next patch/version.
- Automated validation never promotes a candidate.
- Only explicit owner acceptance changes `passed_baseline`.

### New-candidate ordering rule

For an explicitly requested new candidate, **do not update root `VERSION` first**.

Prepare the release bundle first:

```text
docs/PATCH_<version>.md
CHANGELOG.md
docs/START_HERE.md
docs/LOCAL_TESTING.md
docs/TEST_READY_CHECKLIST.md
apps/pc-studio/frontend/src/constants/projectVersion.ts
```

Then update root `VERSION` last, or commit the whole release bundle atomically if the tool supports a multi-file commit. This prevents the structure/version failures caused by a repository that claims a new version before its required metadata exists.

## 3. Inspect only affected ownership/contracts

Use the smallest relevant set:

- backend route/service/model/core owner;
- frontend page/component/API/type owner;
- existing focused regression;
- API/error/data contract if the interface changes;
- architecture/code-structure docs if ownership/configuration changes;
- current patch/testing/checklist docs if acceptance behavior changes.

Do not create a parallel data model when an existing service already owns the domain. Examples:

- source/junction identity → `intersection_network.py`;
- Junction Network read-only live projection → `junction_network_overview.py`;
- camera session/transport → remote camera services/device firmware;
- signal arbitration → `signal_rules.py`;
- isolated network policy overlays → network experiment services/arbiter;
- explanation/evidence → decision context/evidence services.

## 4. Implement in a low-risk sequence

Use this order:

1. domain/service behavior;
2. focused deterministic regression;
3. route/API/type wiring;
4. frontend wiring;
5. contract/scope/architecture docs;
6. release bundle if a new candidate was explicitly requested;
7. full local runner validation.

This keeps defects close to the responsible layer and avoids spending time synchronizing release text around code that is still changing.

Backend responsibilities:

```text
main.py       wiring only
routes/       HTTP translation
services/     domain behavior/state/I-O
models.py     Pydantic contracts
core/         shared infrastructure
```

Frontend responsibilities:

```text
App.tsx       composition/top-level coordination
pages/        page behavior
components/   reusable presentation
api/lib       HTTP/envelope/polling mechanics
types/        shared contracts
```

## 5. Regression design

The normal Windows runner auto-discovers zero-argument `scripts/test_*.py` regressions.

For new behavior:

- prefer one focused test that exercises the semantic invariant directly;
- add a small wiring/structure test if several files must remain connected;
- keep tests deterministic and independent of private runtime data;
- do not make an ordinary automatic `test_*.py` require `--host`, credentials, special hardware or interactive input.

Hardware-only diagnostics should be clearly separated/documented so normal regression does not fail merely because hardware is absent.

## 6. Preserve runtime data and state

Never use `git clean -fd`. Preserve runtime/user data such as datasets, outputs, models, labels, zones/settings, signal/network configuration, camera profiles, traffic histories, and experiments.

When changing stateful services/UI, review:

- backward loading of existing config;
- state restoration after failure;
- source switching/stale-cache behavior;
- reset/delete/reassignment behavior;
- atomic persistence and locks;
- live polling vs unsaved edits.

## 7. Synchronize documentation by responsibility

Use `DOCUMENTATION_MAP.md` rather than changing every document mechanically.

Typical review set:

- current version/candidate: release bundle;
- backend/frontend behavior: function list + current patch/testing docs;
- HTTP/schema: `API_CONTRACTS.md` + typed models/tests;
- stable errors: code + `ERROR_CODES.md`;
- persisted data/coordinates: `DATA_FORMAT.md`;
- architecture/ownership: `ARCHITECTURE.md`, `CODE_STRUCTURE.md`;
- planned scope: `PROJECT_SCOPE.md`, `ROADMAP.md`;
- workflow: `PATCH_PLAYBOOK.md`, agent checklist/guide, human guide.

Keep durable guides version-agnostic and historical sections unchanged.

## 8. Standard owner validation

Routine validation should use one command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The helper:

```text
fast-forward pulls origin/main
→ reloads the pulled runner
→ refreshes Python/training dependencies
→ Python compile
→ structure/version validation
→ every automatic zero-argument scripts/test_*.py regression
→ frontend npm ci + typecheck + production build
→ git diff --check + tracked-tree cleanliness
→ safely replace only AiTL-owned processes on 8000/5173
→ start backend + live smoke
→ start frontend
```

Use individual commands only when diagnosing the stage that failed. This keeps the human workflow stable even as the regression list grows.

Do not report a check as passed if it did not run.

## 9. Code review before handoff

Review the changed area for:

- duplicated ownership/data models;
- service logic in routes or `App.tsx`;
- stale source/frame state;
- polling overlap;
- missing `finally` restoration/cleanup;
- non-atomic persistent writes;
- unbounded storage/UI growth;
- undocumented magic thresholds;
- old-config compatibility;
- provenance ambiguity;
- capability claims stronger than implementation.

For visual editors also check narrow layouts, long IDs, empty/default states, unsaved edits, deletion/reset selection, reassignment confirmation and persistence round-trip.

## 10. Patch archive — only when needed

Construct a ZIP from an explicit changed-file manifest. Every member path starts with `AI_Traffic_Light/`.

Never include:

```text
datasets/
outputs/
*.pt
.venv/
node_modules/
dist/
__pycache__/
*.pyc
```

Run `scripts/validate_patch_zip.py`, compare archive members with the manifest, and calculate SHA-256.

When development is performed directly against GitHub `main`, a ZIP is not required merely for ceremony; the repository commit plus owner pull/test workflow is the source of truth.

## 11. Handoff

Keep the handoff concise:

```text
Version decision
Implemented
Deliberately unchanged/not implemented
Checks actually run
Checks still required locally
Manual acceptance focus
Passed baseline
```

Give the owner the normal one-command validation first. Add only feature-specific manual steps automation cannot perform.

## 12. Acceptance and next patch

The candidate becomes the passed baseline only after explicit owner confirmation. After acceptance, record `passed_baseline` in repository metadata before normal next-version development. If the owner asks to continue hardening before acceptance, stay on the same candidate.
