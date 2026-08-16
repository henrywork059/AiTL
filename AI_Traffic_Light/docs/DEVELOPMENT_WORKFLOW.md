# Development Workflow

This is the current incremental patch workflow for AiTL.

## 1. Establish repository/version state

Inspect current GitHub `main`, then read `AGENTS.md`, `VERSION`, `docs/AI_AGENT_GUIDE.md`, and `docs/AI_AGENT_CHECKLIST.md`.

Current state for this documentation: V023 / `0_2_3` is the candidate; V022 / `0_2_2` is the owner-confirmed passed baseline. Do not promote V023 because automated tests pass.

## 2. Inspect the affected contract and implementation

Inspect the smallest relevant backend routes/services/models/core, frontend page/component/API/types, API/error/data contracts, existing tests, and patch/testing docs. Preserve camera alignment, dataset lifecycle, training/inference, zones, occupancy/flow separation, and simulation-only traffic behavior.

## 3. Implement the smallest cohesive change

Backend: `main.py` wiring only; `routes/` HTTP translation; `services/` business logic; `models.py` Pydantic; `core/` shared envelope/error/logging/request/version infrastructure.

Frontend: `App.tsx` composition only; `pages/` page behavior; `components/` reusable UI; `api.ts`/`apiClient.ts` API access; shared types/constants.

V023 signal policy logic belongs in `services/signal_rules.py`; the camera simulator consumes the resulting phase and must not duplicate arbitration rules.

## 4. Preserve runtime data

Never use `git clean -fd`. Preserve `datasets/`, `outputs/`, `*.pt`, labels, runtime zones/settings, `config/signal_rules.json`, and occupancy/flow/signal-decision history.

## 5. Standard local validation

Use the backend `.venv` for Python validation:

```powershell
python -m compileall .\apps\pc-studio\backend\app .\scripts
python .\scripts\check_structure.py
```

Run all relevant service/regression tests plus live `test_backend_smoke.py` when the backend is running. Frontend release validation uses `npm ci`, `npm run typecheck`, and `npm run build`. Run `git diff --check` from the complete repository.

## 6. Documentation synchronization

Review/update `VERSION`, `CHANGELOG.md`, root/app READMEs, `docs/PATCH_<version>.md`, `LOCAL_TESTING.md`, `TEST_READY_CHECKLIST.md`, `PC_STUDIO_FUNCTION_LIST.md`, API/error docs when contracts change, and current start/versioning/roadmap/agent docs when their state becomes stale.

## 7. Changed-files-only packaging

Construct the ZIP from an explicit manifest. All members begin `AI_Traffic_Light/`. Never include `datasets/`, `outputs/`, `*.pt`, `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, or `*.pyc`.

Run `python .\scripts\validate_patch_zip.py <patch.zip>`, compare its members with the intended manifest, and calculate SHA-256 for ZIP and manifest.

## 8. Owner acceptance

Automated tests establish test readiness only. The owner manually checks the candidate and explicitly confirms acceptance before `passed_baseline` changes.

## 9. Windows update after GitHub upload

The owner uploads the **extracted changed files** to GitHub `main`. Then:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Review local changes/untracked runtime data before pulling and never invent destructive cleanup to force the update.
