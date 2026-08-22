# AI Agent Checklist

Short execution checklist. See `../AGENTS.md`, `DOCUMENTATION_MAP.md`, `PROJECT_SCOPE.md`, and `AI_AGENT_GUIDE.md` for full rules.

## Preflight

- [ ] Inspect current GitHub `main` when repository state matters.
- [ ] Read root `VERSION`; record candidate/status/previous/passed baseline.
- [ ] Confirm whether owner acceptance is explicit.
- [ ] If unaccepted, repair the same candidate unless a new version is explicitly requested.
- [ ] Read affected source, tests, contracts, current patch/testing docs.
- [ ] Classify requested capability: implemented / foundation / simulation-only / planned / out of scope.
- [ ] Identify runtime/user data that must be preserved.

## Change design

- [ ] Define the smallest cohesive change.
- [ ] Keep routes thin, business logic in services, cross-cutting infrastructure in core.
- [ ] Keep `App.tsx` to composition/top-level coordination.
- [ ] Reuse shared types, API client, request IDs, logging, stable errors, atomic persistence.
- [ ] Extend the ranked-scenario/controller architecture rather than duplicating it.
- [ ] Do not hard-code a two-intersection assumption into generic network services.
- [ ] Preserve protected simulated phase semantics.
- [ ] Preserve occupancy / flow / zone-class / experiment / topology distinctions.
- [ ] Preserve AI / simulation / manual provenance.
- [ ] Avoid destructive operations on runtime/user data.

## Documentation

- [ ] Use `DOCUMENTATION_MAP.md` to decide what to update.
- [ ] Keep `VERSION` as the only release-state authority.
- [ ] Keep long-lived guides version-agnostic.
- [ ] Put current candidate detail in `START_HERE`, current patch/testing/checklist docs.
- [ ] Update `PROJECT_SCOPE`/`ROADMAP` if capability scope or dependency order changes.
- [ ] Update API/error/data/architecture docs only when those responsibilities change.
- [ ] Mark capability claims accurately: implemented vs foundation vs planned.
- [ ] Do not rewrite historical patch/changelog facts merely to remove old version strings.

## Validation

- [ ] Python compile.
- [ ] Relevant service/unit/regression tests using backend `.venv` where available.
- [ ] Live API smoke when practical.
- [ ] `python scripts/check_structure.py`.
- [ ] Frontend `npm run typecheck` and `npm run build` when affected or for release validation.
- [ ] `git diff --check` in complete repo.
- [ ] Check current release surfaces against `VERSION`.
- [ ] Check documentation for stale current-state claims and broken file references.
- [ ] Separate actual, targeted/synthetic, and still-required local checks in handoff.

## Packaging

- [ ] Changed-files-only ZIP.
- [ ] Every member begins `AI_Traffic_Light/`.
- [ ] Exclude `datasets/`, `outputs/`, `*.pt`, `.venv/`, `node_modules/`, `dist/`, caches/bytecode.
- [ ] Run patch ZIP validator when available.
- [ ] Compare ZIP member list with intended manifest.
- [ ] Calculate SHA-256 for ZIP and manifest.

## Handoff

- [ ] Explain why version stayed/incremented.
- [ ] List changed files and deliberate non-changes.
- [ ] State capability status/limitations precisely.
- [ ] Provide exact owner acceptance checks.
- [ ] Remind owner to upload extracted changed files, not only the ZIP.
- [ ] Do not promote `passed_baseline` before explicit acceptance.
