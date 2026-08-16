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

- current candidate: V024 / `0_2_4`;
- previous version: V023 / `0_2_3`;
- owner-confirmed passed baseline: V022 / `0_2_2`;
- the owner explicitly requested V024 before explicitly accepting V023, so V023 is not silently promoted.

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

Allowed scope includes receiver/simulated camera frames, local detection/inference, dataset capture/review/manual labeling, local model training, editable traffic zones/counting lines, tracking/analytics, user-defined **simulated** signal timing/rules, simulation-only phase recommendations, and classroom/model-junction experiments.

Do not implement, document, or imply direct control of public-road traffic signals, connections to public traffic-signal cabinets/controllers, bypassing safety interlocks, or production autonomous signal authority. Traffic outputs remain simulation/recommendation/display outputs only.

## 4. Architecture rules

### Backend

Keep:

```text
app/main.py       app creation, middleware, handlers, router wiring only
app/routes/       HTTP translation only; routes stay thin
app/services/     business/state/filesystem/inference/training logic
app/models.py     Pydantic request/response models
app/core/         envelopes, errors, logging, middleware, version metadata, shared persistence helpers
```

Use the central `ErrorCode`/`AppError` mechanisms. Preserve request IDs and structured logging. Backend release metadata comes from root `VERSION` through `app/core/project_version.py`. Shared replace-style JSON persistence for migrated services belongs in `app/core/json_store.py`; services retain domain validation, locks, logging, and stable error translation.

Signal policy ownership for V023+ belongs in `app/services/signal_rules.py`. The camera simulator consumes the resulting protected simulated phase; routes must not implement rule/arbitration logic.

### Frontend

Keep:

```text
src/App.tsx          composition, top-level coordination, page switching
src/pages/           page-level UI/state
src/components/      small reusable UI components
src/api.ts           typed API functions and controlled fallbacks
src/lib/apiClient.ts shared envelope/error handling
src/lib/useSerialPolling.ts non-overlapping periodic async refresh
src/types.ts         shared domain/API types
src/types/           app-specific type modules
src/constants/       navigation/function metadata
```

Do not turn `App.tsx` into a business-logic container. Frontend release fallbacks/navigation use `src/constants/projectVersion.ts`. V024 App-level camera/live-context polling must remain non-overlapping; prefer the shared serial polling helper rather than async `setInterval` loops.

## 5. API contract is stable unless the task changes it

JSON success:

```json
{"ok": true, "data": {}, "meta": {"request_id": "..."}}
```

JSON error:

```json
{"ok": false, "error": {"code": "...", "message": "...", "details": {}}, "meta": {"request_id": "..."}}
```

Binary/image/CSV responses must preserve `X-Request-ID`. Update `docs/API_CONTRACTS.md` when an endpoint changes and synchronize stable error docs/definitions when new stable errors are introduced.

## 6. Runtime data is not patch content

Local working copies may contain valuable untracked/runtime data including `datasets/`, `outputs/`, trained `*.pt` files, manual labels, runtime zones/settings/signal rules, traffic history/flow/signal-decision history, `.venv/`, `node_modules/`, `dist/`, and caches.

Never use destructive cleanup commands such as `git clean -fd`. Never package:

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

Before editing, confirm version state, identify the smallest responsible modules, inspect tests/contracts, and decide whether the work fixes the current candidate or creates a new release.

Preserve existing behavior outside the task. Keep original-image coordinates canonical. Keep sampled occupancy separate from track-derived flow. Keep `counting_region` and `counting_line` analytics-only unless explicitly changed.

For V023+ signal logic:

- user rules may alter bounded **simulated phase durations**, not arbitrary physical control outputs;
- the protected phase order remains vehicle green → vehicle yellow → all-red → pedestrian WALK → pedestrian CLEAR → all-red;
- protected minimum timing, per-phase maximums, maximum-cycle limits, cooldowns, hysteresis/demand memory, stale-data fallback, and incident recovery must remain deterministic;
- Fixed mode uses configured normal timing; Adaptive mode may apply live observation rules; Test mode may additionally use explicit manual accessibility/incident inputs;
- do not claim wheelchair/mobility or fall detection unless a compatible perception source actually exists.

## 8. Testing evidence must be precise

Run relevant checks available in the environment, typically Python compile, backend service/unit/regression tests, live API smoke when practical, `scripts/check_structure.py`, frontend `npm run typecheck`/`npm run build`, `git diff --check`, version scans, runtime-file exclusion scans, and patch ZIP validation.

Report separately: actually run here; targeted/synthetic checks; owner/local checks still required. Automated validation never promotes a candidate.

## 9. Documentation requirements

For each patch review/update as applicable: `VERSION`, `CHANGELOG.md`, `README.md`, affected app READMEs, `docs/PATCH_<version>.md`, `docs/LOCAL_TESTING.md`, `docs/TEST_READY_CHECKLIST.md`, `docs/PC_STUDIO_FUNCTION_LIST.md`, API/error docs, roadmap, and current agent/workflow docs. Do not rewrite historical patch/changelog content incorrectly.

## 10. Patch packaging and handoff

Create a **changed-files-only** ZIP. Every member path must begin with `AI_Traffic_Light/`. Run `scripts/validate_patch_zip.py`, compare the ZIP manifest with the intended change manifest, and provide ZIP/manifest SHA-256 values.

Handoff must include implementation summary, limitations, tests actually run, tests not run, and exact owner acceptance checks. The owner uploads the **extracted changed files** to GitHub `main`; uploading only the ZIP is insufficient.

## 11. Local update safety after GitHub upload

Start with:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
```

Review local/untracked files before pulling. Preserve datasets, training outputs, models, labels, occupancy/flow/signal-decision history, signal-rule configuration, and runtime settings. Then use `git pull --ff-only origin main` when safe. Do not invent cleanup steps to force a pull.

## 12. When uncertain

Choose the smallest safe interpretation that preserves the current accepted behavior and candidate state. State material assumptions in the patch note rather than silently broadening scope.
