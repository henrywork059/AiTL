# Development Workflow

This is the current incremental patch workflow for AiTL. It replaces the old skeleton-era mock-first instructions.

## 1. Establish repository and version state

Inspect current GitHub `main`, then read:

```text
AGENTS.md
VERSION
docs/AI_AGENT_GUIDE.md
docs/AI_AGENT_CHECKLIST.md
```

The current V020 / `0_2_0` state remains a candidate until owner acceptance. Its recorded passed baseline is V017 / `0_1_7`.

Never start a later release solely because V020 exists on `main` or automated tests pass.

## 2. Inspect the affected contract and implementation

Before editing, inspect the smallest relevant set of:

```text
backend routes/services/models/core
frontend page/component/api/types
API_CONTRACTS.md
ERROR_CODES.md
DATA_FORMAT.md / packages/schema/
existing tests
current patch/testing docs
```

Write down the behavior that must remain unchanged. This is especially important for camera alignment, dataset lifecycle, training, inference, zones, and simulation-only traffic logic.

## 3. Implement the smallest cohesive change

Backend layering:

```text
main.py → app wiring only
routes/ → HTTP translation
services/ → business logic
models.py → Pydantic models
core/ → shared envelope/error/logging/request/version infrastructure
```

Frontend layering:

```text
App.tsx → composition/top-level coordination
pages/ → page behavior
components/ → reusable UI
api.ts + lib/apiClient.ts → API access
types → shared contracts
```

Do not mix unrelated cleanup into a feature/fix patch.

## 4. Preserve local runtime data

The working repository can contain untracked data that must survive source updates:

```text
datasets/
outputs/
trained *.pt models
manual labels
runtime settings/zones
```

Do not use `git clean -fd` on the user's working project. Do not treat untracked runtime files as failed source hygiene.

## 5. Backend local environment (Windows / PowerShell)

From the backend directory:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-training.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

When running project test scripts, keep this `.venv` active. If interpreter selection is uncertain, use the backend virtual-environment Python explicitly from the project root.

## 6. Frontend local environment

In a second PowerShell:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
npm run dev
```

## 7. Validation sequence

From `AI_Traffic_Light` with the backend `.venv` active:

```powershell
python -m compileall .\apps\pc-studio\backend\app .\scripts
python .\scripts\check_structure.py
```

Run the relevant service/regression scripts. With the backend running, run:

```powershell
python .\scripts\test_backend_smoke.py
```

Frontend release validation:

```powershell
npm run typecheck
npm run build
```

Repository validation from the complete Git working tree:

```powershell
git diff --check
```

Then inspect the change list and stale runtime version surfaces.

## 8. Documentation synchronization

Every patch should review/update:

```text
VERSION
CHANGELOG.md
README.md
affected app README(s)
docs/PATCH_<version>.md
docs/LOCAL_TESTING.md
docs/TEST_READY_CHECKLIST.md
docs/PC_STUDIO_FUNCTION_LIST.md
```

Update API/error docs only when those contracts change. Update agent/versioning/architecture/roadmap/start docs when the current workflow or state they describe has changed.

## 9. Changed-files-only packaging

Construct the ZIP from the explicit changed-file manifest. Do not zip the project folder wholesale.

All ZIP paths must begin:

```text
AI_Traffic_Light/
```

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

Validate the completed archive:

```powershell
python .\scripts\validate_patch_zip.py <patch.zip>
```

Also inspect the ZIP manifest against the intended changed-file list and calculate SHA-256.

## 10. Owner acceptance is a separate gate

Automated tests establish test readiness, not a passed release. The owner manually checks the UI/features and explicitly confirms acceptance. Only then may `passed_baseline` be promoted.

## 11. Updating the Windows working copy after GitHub upload

The owner uploads the extracted changed files to GitHub `main`. Then start locally with:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
```

Review the output and preserve runtime data. When the tracked working tree permits a safe fast-forward:

```powershell
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Then reinstall/check backend/frontend dependencies as needed and repeat the acceptance checks.
