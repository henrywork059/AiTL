# AI Agent Checklist

Use this as the short execution checklist. See `../AGENTS.md` and `AI_AGENT_GUIDE.md` for full rules.

## Preflight

- [ ] Inspect current GitHub `main` rather than relying on an old snapshot.
- [ ] Read `VERSION` and record `version`, `status`, `previous_version`, and `passed_baseline`.
- [ ] Confirm whether the owner explicitly accepted the current candidate.
- [ ] If not accepted, keep fixing/hardening the current candidate instead of silently incrementing.
- [ ] Read the relevant source, tests, API/error/data contracts, and patch docs.
- [ ] Identify runtime/user data that must be preserved.

## Change design

- [ ] Define the smallest cohesive behavior/refactor required.
- [ ] Keep `main.py` to wiring, routes thin, and business logic in services.
- [ ] Keep `App.tsx` to composition/top-level coordination.
- [ ] Reuse shared API client, types, error codes, logging, and request IDs.
- [ ] Preserve existing accepted/candidate behavior outside the task.
- [ ] Keep traffic decisions simulation/recommendation-only.
- [ ] Avoid destructive operations on datasets, outputs, models, labels, occupancy/flow history, or runtime config.
- [ ] Keep occupancy and flow separate. Only call a passage unique when it comes from a recorded track/counting-line event; document tracker limitations.

## Version and documentation

- [ ] Keep root `VERSION` authoritative.
- [ ] Do not hard-code backend release strings outside `app/core/project_version.py`.
- [ ] Update visible frontend version surfaces for a real version change.
- [ ] Update `VERSION`, `CHANGELOG.md`, `README.md`, affected app README(s), and `docs/PATCH_<version>.md`.
- [ ] Update API/error docs only when those contracts change.
- [ ] Update testing/function/agent/workflow docs when current-state wording changes.

## Validation

- [ ] Run Python compile checks.
- [ ] Run relevant service/unit/regression tests using the backend `.venv`.
- [ ] Run live API smoke tests when practical.
- [ ] Run `python scripts/check_structure.py`.
- [ ] Run frontend `npm run typecheck` and `npm run build` when frontend code is affected or for release validation.
- [ ] Run `git diff --check` in the complete repository.
- [ ] Scan runtime version surfaces for stale release labels.
- [ ] Separate actual, targeted/synthetic, and still-required local tests in the handoff.

## Patch packaging

- [ ] Build a changed-files-only ZIP.
- [ ] Every ZIP member begins with `AI_Traffic_Light/`.
- [ ] Exclude `datasets/`, `outputs/`, `*.pt`, `.venv/`, `node_modules/`, `dist/`, `__pycache__/`, and `*.pyc`.
- [ ] Run `python scripts/validate_patch_zip.py <zip>`.
- [ ] Compare the ZIP manifest with the intended changed-file manifest.
- [ ] Calculate SHA-256.

## Handoff

- [ ] Provide ZIP link, exact manifest, SHA-256, implementation summary, limitations, and test evidence.
- [ ] Provide exact owner acceptance checks.
- [ ] Remind that extracted files—not only the ZIP—must be uploaded to GitHub.
- [ ] Do not mark the candidate passed until the owner explicitly confirms acceptance.
