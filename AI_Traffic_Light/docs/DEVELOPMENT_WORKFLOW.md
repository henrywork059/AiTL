# Development Workflow

This is the durable incremental patch workflow for AiTL. It intentionally does not hard-code the current candidate; root `VERSION` is authoritative.

## 1. Establish repository state

When the task depends on GitHub state, inspect current `main`. Then read:

```text
VERSION
AGENTS.md
docs/DOCUMENTATION_MAP.md
docs/PROJECT_SCOPE.md
docs/AI_AGENT_GUIDE.md
docs/AI_AGENT_CHECKLIST.md
```

Record `version`, `status`, `previous_version`, and `passed_baseline` before deciding whether the work is a same-candidate repair/hardening patch or an explicitly requested new version.

## 2. Apply the candidate gate

- If `version != passed_baseline`, do not silently increment.
- Automated validation never promotes a candidate.
- Only explicit owner acceptance changes the passed baseline.
- If the owner explicitly requests a new version despite an unaccepted candidate, record that deliberate exception in release notes.

## 3. Inspect affected ownership/contracts

Inspect the smallest relevant:

- backend routes/services/models/core;
- frontend pages/components/API/types;
- API/error/data contracts;
- existing regressions;
- architecture/code-structure docs;
- current patch/testing/checklist docs.

Use `PROJECT_SCOPE.md` before adding a planned capability so the implementation does not overclaim its completion state.

## 4. Implement the smallest cohesive change

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

Signal arbitration stays in the signal-rule service. Network topology identity stays in the network service. Explanation projection must not become a second controller. Future cooperation should reuse per-intersection controller instances and explicit transfer/arrival context rather than duplicating scenario logic.

## 5. Preserve runtime data

Never use `git clean -fd`. Preserve runtime/user data such as datasets, outputs, models, labels, zones/settings, signal/network configuration, traffic histories, and experiments.

## 6. Synchronize documentation by responsibility

Use `DOCUMENTATION_MAP.md` rather than changing every document mechanically.

Typical patch docs:

- current version/candidate: `VERSION`, `CHANGELOG`, `START_HERE`, `PATCH_*`;
- owner testing: `LOCAL_TESTING`, `TEST_READY_CHECKLIST`;
- behavior catalog: README/function list;
- interface change: API/error/data contract;
- architecture change: architecture/code structure/agent docs;
- planned scope change: `PROJECT_SCOPE`, `ROADMAP`.

Keep durable guides version-agnostic and historical records historical.

## 7. Standard local validation

From `AI_Traffic_Light/`, use the backend `.venv` where available:

```powershell
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
```

Run relevant service/regression scripts. With backend running, run `scripts/test_backend_smoke.py`.

Frontend release validation:

```powershell
Set-Location .\apps\pc-studio\frontend
npm ci
npm run typecheck
npm run build
```

Repository hygiene from the complete Git working tree:

```powershell
git diff --check
git status --short
```

Do not report a check as passed if it could not run.

## 8. Build a changed-files-only patch

Construct the ZIP from an explicit manifest. Every member path starts with `AI_Traffic_Light/`.

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

Run `scripts/validate_patch_zip.py`, compare archive members with the manifest, and calculate SHA-256 for both ZIP and manifest.

## 9. Handoff

Provide:

- ZIP + manifest;
- version/candidate reasoning;
- exact changed-file list;
- implemented/foundation/planned status;
- limitations;
- checks actually run and not run;
- exact manual acceptance steps.

The owner uploads **extracted changed files**, not only the ZIP.

## 10. Update local copy after GitHub upload

Stop backend/frontend. Then:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

If local changes block a fast-forward, preserve/reconcile them deliberately. Do not invent destructive cleanup.

## 11. Acceptance and next patch

Run the current candidate's acceptance checklist. The candidate becomes the passed baseline only after the owner explicitly confirms acceptance. Only then should normal next-version planning proceed unless the owner directs otherwise.
