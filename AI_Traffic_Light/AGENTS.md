# AGENTS.md — mandatory rules for AiTL coding agents

This file is the first repository instruction for AI coding agents, assistants, and automation working inside `AI_Traffic_Light/`.

## 1. Read order before changing anything

Read these in order:

1. `AGENTS.md` — mandatory repository rules.
2. `VERSION` — current candidate, status, previous version, and owner-confirmed passed baseline.
3. `docs/AI_AGENT_GUIDE.md` — detailed execution rules.
4. `docs/AI_AGENT_CHECKLIST.md` — short preflight/change/test/package checklist.
5. Task-specific contracts/docs, then the current source and tests you intend to change.

Always inspect the current GitHub `main` branch before producing a patch when the task is based on GitHub state. Do not assume an older local snapshot is current.

## 2. Current release gate

At the time of this file update:

- current candidate: V020 / `0_2_0`;
- previous version: `0_1_7`;
- owner-confirmed passed baseline: V017 / `0_1_7`;
- V020 is still a candidate until the owner explicitly confirms its acceptance checks.

Rules:

- Never promote a candidate because automated tests passed.
- Never silently create the next version while the current candidate is unaccepted.
- If the owner reports a problem in an unaccepted candidate, repair the same candidate unless the owner explicitly requests a new version.
- Only change `passed_baseline` after explicit owner acceptance.
- Version skips are allowed only when explicitly requested by the owner.

`VERSION` is authoritative and must contain:

```text
version
status
previous_version
passed_baseline
notes
```

## 3. Project scope and safety boundary

AiTL is a local/student-scale computer-vision and traffic-light simulation prototype.

Allowed scope includes:

- receiver or simulated camera frames;
- local detection/inference;
- dataset capture/review/manual labeling;
- local model training;
- editable traffic zones and zone counts;
- simulated traffic-phase recommendations and GUI signal visualization;
- classroom/model-junction experimentation.

Do not implement, document, or imply:

- direct control of public-road traffic signals;
- connections to public traffic-signal cabinets/controllers;
- bypassing safety interlocks;
- autonomous deployment claims based on prototype detections.

Traffic outputs remain simulation/recommendation/display outputs only.

## 4. Architecture rules

### Backend

Keep:

```text
app/main.py       app creation, middleware, handlers, router wiring only
app/routes/       HTTP translation only; routes stay thin
app/services/     business/state/filesystem/inference/training logic
app/models.py     Pydantic request/response models
app/core/         envelopes, errors, logging, middleware, shared app metadata
```

Use the central `ErrorCode`/`AppError` mechanisms. Preserve request IDs and structured logging.

Project release metadata for backend surfaces comes from root `VERSION` through `app/core/project_version.py`. Do not add literal release versions back into backend health/smoke/template/app wiring. Frontend release fallbacks/navigation use `src/constants/projectVersion.ts`; keep that shared mirror synchronized with root `VERSION` and do not duplicate literals across pages/API fixtures.

### Frontend

Keep:

```text
src/App.tsx          composition, top-level coordination, page switching
src/pages/           page-level UI/state
src/components/      small reusable UI components
src/api.ts           typed API functions and controlled fallbacks
src/lib/apiClient.ts shared envelope/error handling
src/types.ts         shared domain/API types
src/types/           app-specific type modules
src/constants/       navigation/function metadata
```

Do not turn `App.tsx` into a business-logic container. Prefer extracting cohesive logic/components instead of growing unrelated responsibilities in one file.

## 5. API contract is stable unless the task changes it

JSON success:

```json
{
  "ok": true,
  "data": {},
  "meta": {"request_id": "..."}
}
```

JSON error:

```json
{
  "ok": false,
  "error": {
    "code": "...",
    "message": "...",
    "details": {}
  },
  "meta": {"request_id": "..."}
}
```

Binary image responses must include `X-Request-ID`.

When an API changes, update `docs/API_CONTRACTS.md`. When stable error behavior changes, update `docs/ERROR_CODES.md` and the central backend error-code definitions together.

## 6. Runtime data is not patch content

Local working copies may contain valuable untracked/runtime data:

- `datasets/` captures and labels;
- `outputs/` training runs;
- trained `*.pt` models;
- local runtime settings/zones;
- virtual environments and frontend dependencies/builds.

Never use destructive cleanup commands such as `git clean -fd` on the user's working project. Do not overwrite or delete runtime data unless the user explicitly asks for that exact data operation.

Never package these in a source patch:

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

## 7. Change strategy

Before editing:

1. Confirm current version state.
2. Identify the smallest files/responsibilities involved.
3. Inspect existing tests and contracts.
4. Decide whether this is a fix to the current candidate or a new release.

While editing:

- preserve existing working behavior unless the task explicitly changes it;
- prefer small helper modules over duplicated constants/logic;
- avoid speculative framework rewrites;
- avoid mixing unrelated cleanup into a feature patch;
- keep filesystem writes atomic/rollback-aware where data integrity matters;
- keep original-image coordinates as canonical CV data; scale only in presentation layers;
- document assumptions that materially affect later agents.

Optimization means reducing duplication, unclear ownership, accidental coupling, and validation gaps. It does not mean rewriting working code for style alone.

## 8. Testing evidence must be precise

Run the relevant checks available in the environment. Typical validation includes:

```text
python -m compileall
backend service/unit tests
live API smoke tests when backend can run
existing regression tests
python scripts/check_structure.py
npm run typecheck
npm run build
git diff --check
stale-version scan
patch exclusion scan
ZIP integrity/structure check
```

Report three categories separately:

1. **Actually run here** — commands genuinely executed in the agent environment.
2. **Targeted/synthetic checks** — isolated checks that do not equal a full local regression run.
3. **Owner/local checks still required** — hardware/UI/runtime checks the agent could not perform.

Never call a version “passed” based on category 1 or 2. Owner acceptance is separate.

## 9. Documentation requirements

For each patch, keep current-state documentation synchronized. At minimum review/update as applicable:

- `VERSION`
- `CHANGELOG.md`
- `README.md`
- affected app README(s)
- `docs/PATCH_<version>.md`
- `docs/LOCAL_TESTING.md`
- `docs/TEST_READY_CHECKLIST.md`
- `docs/PC_STUDIO_FUNCTION_LIST.md`
- `docs/API_CONTRACTS.md` if APIs changed
- `docs/ERROR_CODES.md` if stable errors changed
- current roadmap/layout/start/versioning/agent docs when their wording is stale

Historical changelog/patch documents may intentionally contain old versions. Do not “clean” history during stale-version scans.

## 10. Patch packaging and handoff

Create a **changed-files-only** ZIP. Every member path must begin with:

```text
AI_Traffic_Light/...
```

Run `scripts/validate_patch_zip.py` on the finished archive. The validator checks path safety, exclusions, and ZIP integrity; compare the manifest against the actual change set to prove changed-files-only scope.

Handoff must include:

- patch ZIP;
- exact changed-files manifest;
- SHA-256;
- implementation summary;
- limitations;
- tests actually run;
- local tests still required;
- exact acceptance checks.

The owner uploads the **extracted changed files** to GitHub `main`; uploading only the ZIP is not sufficient.

## 11. Local update safety after GitHub upload

Start with:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
```

Review untracked files before pulling. Preserve datasets, training outputs, models, labels, and runtime files. Then use a fast-forward-only pull when safe:

```powershell
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Do not invent cleanup steps to force the pull.

## 12. When uncertain

Choose the smallest safe interpretation that preserves the current accepted behavior and candidate state. State the assumption in the patch note rather than silently broadening scope.
