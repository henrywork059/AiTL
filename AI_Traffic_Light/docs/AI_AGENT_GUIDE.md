# AI Agent Guide

This is the detailed operating guide for AI coding agents working on **AI Traffic Light (AiTL)**. `../AGENTS.md` is mandatory and takes priority when the two overlap.

## 1. Mental model

AiTL is a local prototype with this flow:

```text
receiver/simulated camera frame
→ local object detection
→ persisted zone geometry
→ detection-centre zone counts
→ simulation-only traffic recommendation
→ PC Studio visualization
```

It also contains a local data/model workflow:

```text
capture image + metadata
→ manual review/labels
→ managed YOLO dataset
→ local Ultralytics training
→ model registry
→ local live inference
```

No path in this project should turn those recommendations into direct public-road signal control.

## 2. Source-of-truth order

For a development task, resolve state in this order:

1. The owner's explicit current request.
2. Current GitHub `main` content.
3. Root `VERSION` release state.
4. `AGENTS.md` and this guide.
5. API/error/data contracts and current tests.
6. Historical patch/roadmap documents for context only.

Historical docs are not evidence that a candidate passed. Only explicit owner acceptance can promote `passed_baseline`.

## 3. Version-state decision gate

Before coding, read all five root `VERSION` fields.

### If `version != passed_baseline`

Treat the current version as unaccepted unless the owner explicitly says otherwise. Fix/harden that candidate. Do not increment automatically.

### If the owner explicitly confirms the candidate passed

First record the promotion in the next patch/state update so `passed_baseline` reflects the accepted version. Normal future increments then continue from that accepted version unless the owner chooses a different version.

### Never infer acceptance from

- unit tests;
- successful build;
- “looks good” in agent-generated output;
- presence on GitHub `main`;
- a patch document calling something test-ready.

## 4. Preflight repository inspection

For every non-trivial patch, inspect:

```text
VERSION
AGENTS.md
relevant source files
relevant tests
API_CONTRACTS.md if HTTP behavior is involved
ERROR_CODES.md and error_codes.py if errors are involved
DATA_FORMAT.md/schema files if persisted data or coordinates are involved
LOCAL_TESTING.md
TEST_READY_CHECKLIST.md
```

Also inspect nearby modules before adding a new abstraction. Reuse existing services/types/helpers when their responsibility already matches the need.

## 5. Change-size decision rules

Prefer the smallest cohesive change.

Refactor when one of these is true:

- the same project fact/constant is duplicated across multiple runtime surfaces;
- a file owns multiple unrelated responsibilities;
- the same validation/error mapping is repeated;
- a page/service is difficult to test because I/O and business rules are entangled;
- adding the requested feature would otherwise require copy/paste logic.

Do not refactor merely because a file is long. A large training/inference service can be legitimate if its functions are cohesive. Split only when the ownership boundary is clear and tests can verify it.

## 6. Backend implementation protocol

### Routes

Routes translate HTTP input/output. They should:

- accept Pydantic input where applicable;
- call a service;
- return the standard envelope/binary response;
- attach/preserve request IDs;
- avoid filesystem/model/training algorithms.

### Services

Services own business logic and side effects such as:

- capture persistence/deletion;
- labeling and dataset build;
- camera-frame state;
- model discovery/loading;
- inference;
- training;
- zone persistence/counting;
- simulation-only traffic logic.

Prefer explicit service return data over route-layer knowledge of internal files.

### Core

Cross-cutting mechanisms belong in `app/core/`:

- API envelopes;
- stable errors/exceptions;
- logging;
- request middleware;
- project runtime metadata.

Backend release version surfaces must use `app/core/project_version.py`, which validates root `VERSION`. Do not reintroduce literal release strings in `main.py`, health, smoke, or template state.

## 7. Frontend implementation protocol

`App.tsx` should coordinate top-level state/navigation only. Put page behavior in pages, reusable rendering in components, and HTTP behavior in the existing API client/functions.

Use shared TypeScript types rather than recreating response shapes locally. Use `src/constants/projectVersion.ts` for frontend release fallbacks/navigation; do not repeat literal release strings in `api.ts`, Dashboard, or navigation metadata.

For camera/inference overlays:

- canonical boxes/zones remain in source/reference image coordinates;
- scale only for the displayed frame/canvas;
- do not persist browser/canvas pixel coordinates as canonical data;
- keep visibility toggles presentation-only unless the user explicitly requests inference changes.

For mutation APIs, do not silently hide real backend errors behind offline fallback behavior unless the existing contract intentionally does so.

## 8. Data-integrity protocol

Treat these as user data, not disposable build artifacts:

```text
datasets/captures/**
datasets/yolo/**
outputs/training/**
manual label JSON
runtime zone/settings JSON
trained *.pt files
```

When changing deletion/build logic:

- define the complete set of paired files;
- handle partial failures deliberately;
- update counts/status after successful changes;
- preserve stale/rebuild markers for derived datasets;
- test missing-file and failure paths using stable error codes.

Patch archives must never contain those runtime paths/files.

## 9. API/error/logging protocol

Success and errors must keep the established envelopes. Stable domain failures use central error codes and `AppError`; unexpected failures reach the global handler and are logged.

Do not invent one-off error JSON in a route.

Binary image responses are the exception to the JSON body format but still carry `X-Request-ID`.

When adding/changing an endpoint, update the contract docs and tests in the same patch.

## 10. Safety protocol for traffic logic

Allowed language/code intent:

```text
simulation phase
recommendation
visualized signal
model junction
classroom prototype
supervised test
```

Forbidden project direction without a separate explicitly approved and safety-engineered project scope:

```text
public-road controller
physical cabinet integration
production autonomous signal authority
bypass/failsafe defeat
```

A GUI traffic-light graphic must be described as simulated/display-only.

## 11. Testing protocol

Use the backend `.venv` for backend scripts when available. A normal local validation pass should include:

```powershell
python -m compileall .\apps\pc-studio\backend\app .\scripts
python .\scripts\check_structure.py
```

Then run the service/API regression scripts relevant to the patch. With the backend running, run `scripts/test_backend_smoke.py`.

Frontend validation:

```powershell
npm ci
npm run typecheck
npm run build
```

Repository hygiene:

```text
git diff --check
version-surface check
forbidden runtime/generated-file scan
patch ZIP validation
```

Do not claim a command passed unless it actually ran in the current environment.

## 12. Patch assembly protocol

Build the archive from the known changed-file list, not by zipping the project root.

Expected member shape:

```text
AI_Traffic_Light/VERSION
AI_Traffic_Light/CHANGELOG.md
AI_Traffic_Light/apps/...
AI_Traffic_Light/docs/...
```

Never include runtime/generated paths. Run:

```powershell
python .\scripts\validate_patch_zip.py <patch.zip>
```

Then independently compare the ZIP manifest with the intended change manifest.

## 13. Handoff protocol

A useful handoff tells the owner exactly:

- why the patch stays on or increments the current version;
- what files changed;
- what behavior changed and what did not;
- what automated/targeted checks ran;
- what could not be tested;
- what manual acceptance checks to perform;
- SHA-256 of the ZIP.

Do not write “passed baseline” until the owner explicitly confirms manual acceptance.

## 14. Common failure patterns to avoid

- Starting a new version while the current candidate is still unaccepted.
- Hard-coding release strings in multiple backend surfaces.
- Putting service logic into FastAPI routes.
- Growing `App.tsx` with page-specific business logic.
- Treating datasets/training outputs as disposable Git clutter.
- Running `git clean -fd` on the user's working copy.
- Packaging the full repository instead of changed files.
- Calling synthetic/unit checks a full regression pass.
- Editing historical changelog versions during a stale-version scan.
- Describing simulated recommendations as real traffic control.

## 15. When context is incomplete

Inspect the repository first. If a safe, narrow assumption is possible, make it explicit in `docs/PATCH_<version>.md` and continue. Do not broaden scope just to avoid uncertainty.
