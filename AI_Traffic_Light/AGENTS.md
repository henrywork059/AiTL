# AGENTS.md — mandatory rules for AiTL coding agents

This is the first repository instruction for any AI coding agent, assistant, or automation working inside `AI_Traffic_Light/`.

## 1. Read order before changing anything

Read in this order:

1. `VERSION` — authoritative candidate, status, previous version, passed baseline, and notes.
2. `AGENTS.md` — mandatory repository rules.
3. `docs/DOCUMENTATION_MAP.md` — which documents are authoritative, current, durable, or historical.
4. `docs/PROJECT_SCOPE.md` — implemented/foundation/planned capability boundaries.
5. `docs/AI_AGENT_GUIDE.md` and `docs/AI_AGENT_CHECKLIST.md` — execution protocol.
6. Task-specific contracts, source, tests, and current patch/testing docs.

When a task depends on repository state, inspect current GitHub `main` before producing a patch. Do not substitute an older local snapshot, conversation summary, historical patch note, or remembered version for current repository evidence.

## 2. Release-state gate

`VERSION` is the only release-state authority. It must contain:

```text
version
status
previous_version
passed_baseline
notes
```

Rules:

- Never promote a candidate because automated tests/builds pass.
- Never infer acceptance because code is on GitHub `main`.
- If `version != passed_baseline`, treat the current version as unaccepted unless the owner explicitly says otherwise.
- Repair an unaccepted candidate as the same candidate unless the owner explicitly requests a new version.
- Change `passed_baseline` only after explicit owner acceptance.
- Version skips are allowed only when explicitly requested by the owner.
- Long-lived guides must not duplicate a hard-coded "current version" snapshot. Current candidate detail belongs in `VERSION`, `docs/START_HERE.md`, and `docs/PATCH_<version>.md`.

## 3. Project scope and safety boundary

AiTL is a local/student-scale computer-vision and traffic-light simulation prototype.

Allowed work includes camera receiving/simulation, local detection/inference, dataset capture/review/manual labeling, local model training, camera-aligned zones/counting lines, tracking/analytics, simulated signal policies, ranked scenarios, seeded synthetic experiments, generic intersection/network metadata, explanation context, and model-junction/classroom demonstrations.

Do not implement, document, or imply:

- direct public-road signal control;
- traffic-cabinet/controller integration;
- bypassing signal safety interlocks;
- certified or production autonomous authority;
- a perception capability that the active detector/source does not actually provide.

Traffic decisions and phases remain simulation/recommendation/display outputs only. Use `docs/PROJECT_SCOPE.md` when describing planned capabilities.

## 4. Architecture ownership

### Backend

```text
app/main.py       app creation, middleware, handlers, router wiring only
app/routes/       HTTP translation only; routes stay thin
app/services/     business/state/filesystem/inference/training logic
app/models.py     Pydantic request/response models
app/core/         envelopes, errors, logging, middleware, version metadata, shared persistence
```

Use central `ErrorCode`/`AppError`, request IDs, and structured logging. Backend release metadata comes from root `VERSION` through `app/core/project_version.py`.

Signal-policy ownership stays in `app/services/signal_rules.py`. Exactly one eligible ranked scenario wins an arbitration evaluation. Protected phase ordering/timing guards remain controller-owned. `app/services/simulation_experiments.py` remains isolated from live camera/controller state. `app/services/network_simulation_experiments.py` owns the isolated current multi-mode two-intersection benchmark and protected simulation-only policy layers; it must not mutate live camera/controller state. `app/services/network_policy_arbiter.py` is the pure V031 network-overlay priority selector: it chooses one higher-level overlay owner per intersection/tick but does not mutate timing itself. `app/services/decision_evidence.py` owns the additive normalized V031 network evidence projection/export and must not perform signal arbitration.

Network/topology identity belongs in `app/services/intersection_network.py`. Structured live explanation projection belongs in `app/services/decision_context.py`; normalized stored network-experiment evidence belongs in `app/services/decision_evidence.py`. V031 network transfer, cooperation, pedestrian-aware, vehicle-class-aware, scenario, and emergency evidence are simulator evidence only. A configured/live neighbour link still does not imply observed real transfer, live cooperation, live class priority, emergency priority, or multi-camera live-controller operation.

### Frontend

```text
src/App.tsx          composition/top-level coordination
src/pages/           page-level UI/state
src/components/      reusable UI
src/api.ts           typed API functions
src/lib/apiClient.ts envelope/error handling
src/lib/useSerialPolling.ts non-overlapping async refresh
src/types.ts/types/  shared domain/API types
src/constants/       navigation/release metadata
```

Do not turn `App.tsx` into a page-specific business-logic container. Prefer serial polling for periodic async work that could overlap. Dense telemetry should remain grouped with tabs/panels/filters/pagination rather than a single unbounded page.

## 5. Data and semantics invariants

Preserve these distinctions unless the task explicitly changes them:

- **occupancy** = sampled presence in a frame/region;
- **flow** = track-derived line/region events;
- **zone/class counts** = per-frame detector observations for scenario conditions;
- **experiment telemetry** = isolated synthetic simulator/controller output;
- **network links** = configured topology metadata in live state; `network-experiments` may generate explicit synthetic transfer, predicted-arrival, coordination, pedestrian, vehicle-class, and emergency events over a selected link;
- **observation provenance** must identify simulation/manual sources rather than presenting them as AI detections.

Canonical boxes remain in original-image coordinates. Zone geometry remains in the validated reference coordinate system; display scaling is presentation-only.

## 6. API contract

JSON success:

```json
{"ok": true, "data": {}, "meta": {"request_id": "..."}}
```

JSON error:

```json
{"ok": false, "error": {"code": "...", "message": "...", "details": {}}, "meta": {"request_id": "..."}}
```

Binary/image/CSV responses preserve `X-Request-ID`. Update `docs/API_CONTRACTS.md` when HTTP behavior changes and synchronize `error_codes.py` with `docs/ERROR_CODES.md` when stable errors change.

## 7. Runtime/user data is not patch content

Never use destructive cleanup such as `git clean -fd`. Preserve local runtime/user data, including:

```text
datasets/
outputs/
*.pt
manual labels
config/zones.json
config/runtime_settings.json
config/signal_rules.json
config/intersections.json
.venv/
node_modules/
dist/
caches
```

Patch archives must never contain runtime/generated data.

## 8. Change strategy

Before editing:

1. resolve release state from `VERSION`;
2. identify the smallest responsible modules;
3. inspect affected tests/contracts/data formats;
4. decide whether the request repairs the current candidate or explicitly starts a new version;
5. write down material assumptions rather than silently broadening scope.

Extend the existing architecture instead of building a parallel controller or duplicate data model. For multi-intersection, emergency, pedestrian, vehicle-class-aware, and explainability work, follow the dependency/evidence boundaries in `docs/PROJECT_SCOPE.md` and `docs/ROADMAP.md`.

## 9. Testing evidence must be precise

Run relevant checks available in the environment, normally:

- Python compile;
- focused backend service/unit/regression tests;
- live API smoke when practical;
- `scripts/check_structure.py`;
- frontend typecheck/build when affected or for release validation;
- `git diff --check` in the complete repository;
- version/runtime-file scans;
- patch ZIP validation.

Report separately:

- checks actually run in the current environment;
- targeted/synthetic checks;
- checks still required on the owner's complete local repository.

Never describe a check as passed if it did not run.

## 10. Documentation policy

Use `docs/DOCUMENTATION_MAP.md` before editing documentation.

For a patch, update only documents whose responsibilities changed. Keep long-lived guidance version-agnostic. Put current-candidate facts in `START_HERE.md`, `PATCH_<version>.md`, `LOCAL_TESTING.md`, and `TEST_READY_CHECKLIST.md`. Do not rewrite historical changelog/patch facts to make them look current.

Claims must match implementation status:

- **implemented** — working code path exists and has relevant evidence;
- **foundation** — schema/service/context exists but target behavior is inactive;
- **simulation-only** — works only in the local simulator/test path;
- **planned** — no completed behavior yet;
- **out of scope** — explicitly excluded.

## 11. Patch packaging and handoff

Create a **changed-files-only** ZIP. Every member starts with `AI_Traffic_Light/`. Run `scripts/validate_patch_zip.py` when available, compare the ZIP member list with the intended manifest, and calculate SHA-256.

Handoff must include:

- why the patch stays on/increments the version;
- changed files;
- behavior/doc changes and deliberate non-changes;
- tests/checks actually run;
- checks not run;
- exact owner acceptance checks;
- ZIP/manifest hashes.

The owner uploads the **extracted changed files** to GitHub `main`; uploading only the ZIP is insufficient. Prefer applying the overlay locally and pushing one atomic Git commit (or merging one PR) rather than uploading files piecemeal. If web upload is used, verify every manifest member is present in the same resulting candidate commit before treating GitHub as the patch base.

After explicit owner acceptance, update `passed_baseline` in repository metadata before normal next-version development. When the owner's Git workflow permits it, also create an immutable tag such as `passed-0_3_1` on the accepted commit so a known-good checkout/rollback target exists; the root `VERSION` file remains the release-state authority.

## 12. Local update safety after GitHub upload

Start with:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Only pull when the working tree situation is understood. Preserve runtime data and do not invent cleanup steps to force a pull.

## 13. When uncertain

Choose the smallest safe interpretation that preserves accepted behavior, current candidate state, data semantics, and the prototype-only safety boundary. If repository evidence and an old document disagree, prefer current code/contracts/`VERSION` and update the stale durable document as part of the patch when appropriate.

### Network policy-arbitration rule

In the isolated network benchmark, ranked scenarios are the controller-owned base policy and higher-level network overlays must not compete through call order. Use the pure network policy arbiter and one overlay owner per intersection/tick. Current priority order is incident hold > active pedestrian crossing > simulated emergency priority > pedestrian max-wait > configured regular vehicle-class priority > network cooperation. Post-advisory signal reads must use non-reapplying snapshot semantics. The existing seven modes are comparison/ablation modes; do not claim class-aware and emergency-priority overlays are simultaneously integrated unless a future explicit integrated mode is implemented and tested.

### Persistent decision-evidence rule

V031 `decision_evidence` is an additive schema-versioned projection over detailed experiment histories. Keep stable fields/context/provenance/source references, deterministic evidence IDs, and backward projection for older stored runs. Do not move arbitration or timing logic into `decision_evidence.py`, do not delete detailed mode-specific histories merely because the normalized ledger exists, and do not embed volatile random run IDs inside individual records when that would break seeded repeatability.

### Vehicle-class evidence rule

V030 regular class generation is synthetic simulator input. Keep `synthetic_vehicle_class_demand` provenance on class-aware experiment evidence. Unknown/unmapped regular labels normalize to `other`. Do not present V030 class profiles or class-priority outcomes as detector accuracy, live transit priority, or public-road authority. A configured class weight of `1.0` is neutral; class-aware timing must remain within the existing protected phase/cycle bounds and must not shorten active pedestrian WALK/CLEAR demand.
