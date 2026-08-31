# Documentation Map and Authority

This document explains what each AiTL document is for and prevents stale historical text from being mistaken for current project state.

## 1. Authority order

When two sources disagree, use this order:

1. **Owner's explicit current instruction** — decides intent and acceptance.
2. **Current GitHub `main` source/tests/contracts** — decides what is actually implemented.
3. **Root `VERSION`** — decides candidate/baseline release state.
4. **`AGENTS.md` + `docs/PROJECT_SCOPE.md`** — mandatory development/scope boundaries.
5. **API/error/data contracts** — decide stable interfaces and semantics.
6. **Current candidate docs** — explain the current patch and acceptance checks.
7. **Durable guides** — explain workflow/architecture without owning current release state.
8. **Historical patch/changelog docs** — history only.

A historical patch note is never proof that a version passed.

## 2. Current-state documents

These are intentionally updated when the active candidate changes:

| Document | Responsibility |
| --- | --- |
| `VERSION` | Canonical `version`, `status`, `previous_version`, `passed_baseline`, notes |
| `docs/START_HERE.md` | Concise current candidate orientation |
| `docs/PATCH_<version>.md` | Exact candidate changes, limitations, validation, acceptance notes |
| `docs/LOCAL_TESTING.md` | Commands and detailed current-candidate local checks |
| `docs/TEST_READY_CHECKLIST.md` | Owner acceptance checklist |
| `CHANGELOG.md` | Chronological release/candidate history |

Treat those six release surfaces plus the shared frontend version constant as a **release bundle**. For a new candidate, prepare the supporting files first and update root `VERSION` last (or commit the whole release bundle atomically). This avoids a temporary repository state where `VERSION` points at documentation/version surfaces that do not exist yet.

Do not duplicate current version numbers into unrelated durable guides unless the text is clearly an example or historical reference.

## 3. Durable instruction/guidance documents

These should stay useful across version changes:

| Document | Responsibility |
| --- | --- |
| `AGENTS.md` | Mandatory AI/coding-agent repository rules |
| `docs/PATCH_PLAYBOOK.md` | Fast-path patch order, release-bundle rule, regression naming and handoff definition-of-done |
| `docs/AI_AGENT_GUIDE.md` | Detailed AI development protocol |
| `docs/AI_AGENT_CHECKLIST.md` | Short execution checklist |
| `docs/HUMAN_GUIDE.md` | Human orientation, safe update/test/use workflow |
| `docs/DEVELOPMENT_WORKFLOW.md` | Incremental patch process |
| `docs/VERSIONING.md` | Candidate/acceptance/version rules |
| `docs/PROJECT_SCOPE.md` | Implemented/foundation/planned/out-of-scope capability definitions |
| `docs/ARCHITECTURE.md` | Current architecture and ownership boundaries |
| `docs/CODE_STRUCTURE.md` | Module/folder responsibilities |
| `docs/API_CONTRACTS.md` | HTTP contract |
| `docs/ERROR_CODES.md` | Stable error-code contract |
| `docs/DATA_FORMAT.md` | Persisted/data-coordinate semantics |
| `docs/DEBUGGING_AND_LOGGING.md` | Diagnostic/logging guidance |
| `docs/GUI_PLAN.md` | Durable PC Studio UI structure/presentation guidance |
| `apps/pc-studio/backend/README.md` | Backend responsibilities/run guidance |
| `apps/pc-studio/frontend/README.md` | Frontend responsibilities/run/presentation guidance |
| `docs/PC_STUDIO_FUNCTION_LIST.md` | Current functional capability catalog |
| `docs/ROADMAP.md` | Planned dependency order and evidence milestones |

For routine coding work, read the mandatory authority files and then use `PATCH_PLAYBOOK.md` as the short execution path. Open the longer guides only for the parts of the task that need them.

## 4. Historical documents

Older `docs/PATCH_*.md`, one-off validation notes, and previous changelog sections are historical evidence. Preserve their original release context. Do not edit old version numbers just because a repository-wide text search finds them.

## 5. Documentation update matrix

For each patch, update documents based on what changed:

| Change type | Minimum docs to review |
| --- | --- |
| Candidate/version state | release bundle: `VERSION`, `CHANGELOG`, `START_HERE`, patch/testing/checklist, frontend version source |
| Backend/frontend behavior | `README`, function list, patch doc, testing/checklist |
| API endpoint/schema | `API_CONTRACTS`, models/types tests, patch/testing docs |
| Stable error | `error_codes.py`, `ERROR_CODES`, tests |
| Persisted data/coordinates | `DATA_FORMAT`, architecture/patch/tests |
| Architecture/ownership | `ARCHITECTURE`, `CODE_STRUCTURE`, agent guides |
| Planned scope/priorities | `PROJECT_SCOPE`, `ROADMAP` |
| Workflow/packaging | `PATCH_PLAYBOOK`, agent guides/checklist, `DEVELOPMENT_WORKFLOW`, `HUMAN_GUIDE` |

## 6. Writing rules

- Use exact implementation status: **implemented**, **foundation**, **simulation-only**, **planned**, or **out of scope**.
- Keep limitations adjacent to capability claims.
- Separate sampled occupancy, track-derived flow, simulator telemetry, and configured topology.
- Label synthetic/manual inputs as synthetic/manual.
- Do not describe a configured interface or schema as an active behavior.
- Avoid phrases such as "will eventually" in current function lists; place future work in `PROJECT_SCOPE.md`/`ROADMAP.md` instead.
- Prefer links to the authority rather than copying a release-state fact into many files.
- When code and durable architecture docs disagree, fix the durable docs in the same candidate rather than leaving the contradiction for the next agent.

## 7. Review before handoff

Before handing off a documentation-affecting patch, verify:

- current release bundle is synchronized with root `VERSION`;
- no durable guide contains an obsolete "current version" claim;
- links/file references exist;
- implemented/foundation/planned labels match code;
- current API/error docs match source;
- architecture docs match actual production configuration (for example framebuffer/transport ownership);
- acceptance instructions describe checks the owner can actually perform;
- safety wording remains prototype/simulation-only;
- a focused zero-argument `scripts/test_*.py` regression exists when a durable invariant can be checked automatically.
