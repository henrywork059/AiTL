# Patch Playbook — fast, low-risk AiTL development

This is the concise execution path for future AiTL patches. `../AGENTS.md` remains mandatory and `VERSION` remains the release-state authority.

## 1. Five-minute preflight

Before editing code, capture these facts:

```text
current version:
status:
previous version:
passed baseline:
requested version change? yes/no
affected owner modules:
affected API/data contracts:
focused regression to add/run:
runtime/user data at risk:
```

Read only what the task needs after the mandatory authority files. Do not sweep the entire repository before every small change.

Use this ownership shortcut:

| Change | Start here |
| --- | --- |
| ESP transport/camera session | device-camera firmware, `remote_camera.py`, `remote_camera_manager.py` |
| selected frame/simulation | `camera_frames.py` |
| junction/source/topology mapping | `intersection_network.py` |
| Junction Network UI projection | `junction_network_overview.py`, `JunctionNetworkPage.tsx` |
| signal policy | `signal_rules.py` |
| isolated network simulation | `network_simulation_experiments.py`, `network_policy_arbiter.py` |
| explanation/evidence | `decision_context.py` / `decision_evidence.py` |
| frontend HTTP | typed API helper + shared API client |
| persistence | owning service + shared atomic JSON helper |

## 2. Decide version before implementation

- If the current candidate is unaccepted and the owner asks to continue/fix/review it, stay on the **same candidate**.
- Increment the patch (`Z`) only when the owner explicitly requests the next patch/version.
- Never change `passed_baseline` without explicit owner acceptance.

For a new candidate, **prepare release metadata first but update root `VERSION` last**. This prevents the repository from temporarily claiming a version whose patch doc/changelog/frontend/current-testing docs do not exist yet.

## 3. Implement in this order

1. **Domain/service behavior** — smallest responsible module.
2. **Focused regression** — prove the new invariant or reproduce/fix the bug.
3. **Thin route/API/type wiring** — only if required.
4. **Frontend page/component wiring** — only if required.
5. **Contract/scope docs** — only responsibilities that changed.
6. **Release bundle** — current candidate files together.
7. **Full owner validation** — one normal runner command.

Do not begin with version/document churn before the implementation shape is known.

## 4. Regression rule that saves time

`scripts/update_test_run.ps1` automatically runs every zero-argument `scripts/test_*.py` file except its documented preflight/hardware-only exclusions.

Therefore:

- name ordinary offline regressions `test_<feature>.py`;
- make them deterministic and runnable with no extra arguments;
- test service behavior directly before route/UI structure;
- add a structure/wiring assertion when a feature depends on several files being connected;
- do **not** create a normal `test_*.py` file that unexpectedly requires `--host`, special hardware, credentials or user input.

A focused regression should verify the important semantic claim, not just that a string/file exists.

Cheap repository guards run before dependency refresh. A broken release bundle, stale durable architecture, runner syntax/structure issue, or Python compile error should therefore fail before time is spent on pip/npm work.

## 5. Release bundle — treat it as one unit

When a new candidate is explicitly requested, synchronize these before changing `VERSION`:

```text
docs/PATCH_<new-version>.md
CHANGELOG.md
docs/START_HERE.md
docs/LOCAL_TESTING.md
docs/TEST_READY_CHECKLIST.md
frontend/src/constants/projectVersion.ts
```

Then update:

```text
VERSION
```

Also update only when affected:

```text
docs/API_CONTRACTS.md
docs/ERROR_CODES.md
docs/DATA_FORMAT.md
docs/ARCHITECTURE.md
docs/CODE_STRUCTURE.md
docs/PROJECT_SCOPE.md
docs/ROADMAP.md
docs/PC_STUDIO_FUNCTION_LIST.md
```

If the tool supports an atomic multi-file commit, prefer committing the release bundle atomically. If it does not, keep `VERSION` unchanged until the supporting files are ready and set `VERSION` last.

## 6. Documentation claim check

For every new feature sentence, ask:

```text
Is this implemented, foundation, simulation-only, planned, or out of scope?
What source actually produces this value?
Does more than one camera exist, or does more than one camera feed inference simultaneously?
Is a configured topology link being mistaken for measured movement/cooperation?
Is synthetic/manual evidence being described as AI perception?
```

Put the limitation beside the capability, not several paragraphs later.

## 7. Code-review checklist before handoff

Review changed code for:

- ownership violations / duplicated data models;
- stale state after source switching;
- async polling overlap;
- missing state restoration on failure (`finally` where appropriate);
- filesystem writes that bypass atomic persistence;
- unbounded lists/history/UI growth;
- magic thresholds whose meaning is undocumented;
- compatibility with existing saved config;
- nullable/optional fields that are accidentally normalized into a value;
- source/provenance ambiguity;
- routes containing service logic;
- release/docs claiming behavior that code does not perform.

For frontend visual editors also check:

- empty/default state;
- unsaved edits vs live polling;
- selection after delete/reset;
- resize/narrow-screen behavior;
- identifiers/long text overflow;
- destructive/reassignment confirmation;
- persistence round-trip;
- whether an explicit `None`/disabled choice actually survives save/reload.

## 8. One owner validation command

Routine owner validation should use the repository runner rather than an ad-hoc command list:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The normal command:

1. fast-forwards `main` and reloads the newly pulled runner;
2. runs cheap compile/structure/release/runner guards first;
3. refreshes Python dependencies only when backend requirement manifests changed in that Git update;
4. refreshes frontend dependencies only when `package.json`/`package-lock.json` changed or `node_modules` is missing;
5. auto-runs the offline regression suite;
6. typechecks/builds the frontend;
7. checks tracked-tree cleanliness;
8. safely replaces an old AiTL PC Studio instance;
9. runs live backend smoke and relaunches PC Studio.

Full validation is still performed even when dependency installation is skipped. Only redundant dependency installation is avoided.

If the local environment is damaged or a dependency was removed manually, force a dependency refresh with:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -RefreshDependencies
```

Direct `-SkipUpdate` use is deliberately conservative and refreshes dependencies because it has no Git-update manifest hint.

Use individual commands only when debugging a failing stage.

## 9. Handoff format

Keep the handoff short and evidence-based:

```text
Version decision:
Implemented:
Deliberately not implemented:
Automated checks actually run:
Checks not run / owner must run:
Manual acceptance focus:
Passed baseline remains:
```

Never say a test passed unless it actually ran. Never promote the candidate based on agent judgment.
