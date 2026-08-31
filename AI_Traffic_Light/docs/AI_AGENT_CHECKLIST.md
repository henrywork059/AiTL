# AI Agent Checklist

Short execution checklist. Read `../AGENTS.md` first. For routine work, use `PATCH_PLAYBOOK.md`; open `AI_AGENT_GUIDE.md`, `PROJECT_SCOPE.md`, and task-specific contracts when needed.

## 1. Preflight — record facts before editing

- [ ] Inspect current GitHub `main` when repository state matters.
- [ ] Read root `VERSION`; write down `version`, `status`, `previous_version`, `passed_baseline`.
- [ ] Confirm whether the owner explicitly requested a new patch/version or asked to continue/repair the current candidate.
- [ ] If the candidate is unaccepted, keep the same candidate unless a new version was explicitly requested.
- [ ] Identify the smallest owning modules and existing focused tests.
- [ ] Identify affected API/data/error/architecture contracts.
- [ ] Classify the requested capability: implemented / foundation / simulation-only / planned / out of scope.
- [ ] Identify runtime/user data that must not be touched.

## 2. Change design — one owner per behavior

- [ ] Keep routes thin; business logic in services; cross-cutting infrastructure in core.
- [ ] Keep `App.tsx` to composition/top-level coordination.
- [ ] Reuse shared types/API client/request IDs/logging/stable errors/atomic persistence.
- [ ] Extend existing data models/services rather than creating a parallel controller, topology store or camera registry.
- [ ] Preserve occupancy / flow / zone-class / experiment / topology distinctions.
- [ ] Preserve AI / simulation / manual provenance.
- [ ] Preserve the single selected `CameraFrameService` source unless the task explicitly implements and tests a different architecture.
- [ ] Avoid destructive operations on runtime/user data.

## 3. Implement in the low-risk order

- [ ] Domain/service behavior first.
- [ ] Add/update a focused deterministic regression for the semantic invariant.
- [ ] Add route/API/type wiring only if required.
- [ ] Add frontend page/component wiring only if required.
- [ ] Review failure cleanup/state restoration (`finally` where appropriate).
- [ ] Review backward compatibility for saved config/data.
- [ ] Review empty/default/reset/delete/reassignment states for editable UI.

### Automatic regression naming

- [ ] Ordinary offline regressions are zero-argument `scripts/test_*.py` so the normal runner auto-discovers them.
- [ ] Hardware/interactive scripts that require `--host`, credentials, special firmware or user input are not introduced as ordinary automatic `test_*.py` regressions unless the runner explicitly excludes/documents them.

## 4. Documentation by responsibility

- [ ] Use `DOCUMENTATION_MAP.md` rather than editing every document.
- [ ] Fix durable architecture/ownership docs if code made them stale.
- [ ] Update API/error/data docs when their actual contract changed.
- [ ] Update function/scope docs when capability status changed.
- [ ] Keep durable guides version-agnostic.
- [ ] Do not rewrite historical patch/changelog facts.

## 5. New-version release bundle

Only when the owner explicitly requested a new candidate:

- [ ] Prepare `PATCH_<version>.md`.
- [ ] Add `CHANGELOG.md` section without altering older history.
- [ ] Update `START_HERE.md`.
- [ ] Update `LOCAL_TESTING.md`.
- [ ] Update `TEST_READY_CHECKLIST.md`.
- [ ] Update frontend shared `projectVersion.ts`.
- [ ] **Update root `VERSION` last**, or commit the full release bundle atomically when tooling permits.
- [ ] Never change `passed_baseline` without explicit owner acceptance.

For same-candidate repairs/hardening, do not create a new patch number and do not rewrite the release bundle unnecessarily; update only current docs whose content changed.

## 6. Validation

- [ ] Python compile.
- [ ] `python scripts/check_structure.py`.
- [ ] Relevant focused/inherited regressions using backend `.venv` where available.
- [ ] Frontend `npm run typecheck` and `npm run build` when affected or for release validation.
- [ ] Live API smoke when practical.
- [ ] `git diff --check` in the complete repo.
- [ ] Tracked working tree remains clean after tests.
- [ ] Current release-document consistency regression passes.
- [ ] Separate checks actually run from checks still required locally.

For routine owner validation, prefer the single normal command:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Use individual commands only to diagnose a failing stage.

## 7. Packaging — only when a patch archive is required

- [ ] Changed-files-only ZIP.
- [ ] Every member begins `AI_Traffic_Light/`.
- [ ] Exclude `datasets/`, `outputs/`, `*.pt`, `.venv/`, `node_modules/`, `dist/`, caches/bytecode.
- [ ] Run patch ZIP validator.
- [ ] Compare ZIP member list with intended manifest.
- [ ] Calculate SHA-256 for ZIP and manifest.

## 8. Handoff

- [ ] Explain version decision in one sentence.
- [ ] List meaningful behavior/doc changes and deliberate non-changes.
- [ ] State capability status/limitations precisely.
- [ ] State checks actually run; never report unrun checks as passed.
- [ ] Give one exact owner validation command plus only the manual acceptance checks that automation cannot cover.
- [ ] Keep `passed_baseline` unchanged until explicit owner acceptance.
