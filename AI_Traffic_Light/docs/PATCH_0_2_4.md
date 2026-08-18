# Patch 0_2_4 — Maintenance hardening and polling optimization

## Release state

- Candidate: V024 / `0_2_4`
- Previous version/candidate: V023 / `0_2_3`
- Owner-confirmed passed baseline: V022 / `0_2_2`
- The owner explicitly requested V024 before explicitly accepting V023; this patch does not retroactively promote V023.

## Purpose

V024 is a bounded maintenance release. It reduces duplicated persistence mechanics, closes in-process synchronization gaps, and prevents overlapping top-level frontend polling requests. It intentionally avoids changing API contracts, adaptive-signal semantics, model behavior, datasets, or the established PC Studio visual system.

## Backend changes

### Shared atomic JSON persistence

Added `app/core/json_store.py` with:

- UTF-8 `read_json`;
- unique same-directory temporary files via `tempfile.mkstemp`;
- JSON serialization before target replacement;
- flush and `os.fsync` on the temporary file;
- atomic `os.replace`;
- temporary-file cleanup if serialization/write/replace fails.

Migrated:

- `runtime_settings.py`;
- `zones.py`;
- `model_registry.py`.

Domain validation, logging, return values, and stable error codes remain owned by those services. Signal-rule persistence is intentionally unchanged in V024 to avoid broadening this maintenance patch.

### Synchronization

- Zone save now holds the same service lock used for zone reads before replacing the configuration.
- Model registry now uses an `RLock` around discovery/default/path/delete/metadata transitions, allowing nested registry calls while preventing process-local races.

## Frontend changes

Added `src/lib/useSerialPolling.ts`. It schedules the next async poll only after the current task settles, uses cleanup-aware `setTimeout`, and reports uncaught poll errors through the existing frontend logger.

Migrated App-level:

- camera status polling;
- Live AI traffic-state + active-zone context polling.

The live trained-model detection loop already self-schedules after each request and remains unchanged. Page-specific analytics/Traffic Logic polling is not refactored in this release; further consolidation can be evaluated separately.

## Validation / guardrails

- Added `scripts/test_atomic_json_store.py` and `scripts/test_frontend_polling_structure.py`.
- `check_structure.py` now requires the shared persistence helper, serial polling hook, and atomic regression test.
- Structure validation checks that migrated persistence services call `write_json_atomic` and do not reintroduce fixed `.tmp` paths/direct JSON writes.
- Structure validation checks App-level periodic refresh uses `useSerialPolling` and no raw `window.setInterval`.

## Deliberate non-changes

- no API endpoint/schema changes;
- no stable error-code changes;
- no signal-rule timing/arbitration changes;
- no dataset/model format changes;
- no dependency-version changes;
- no V023 visual-system changes;
- no physical/public-road traffic control.

## Runtime data

Do not package or overwrite local `datasets/`, `outputs/`, trained `*.pt`, labels, runtime zones/settings/signal rules, analytics histories, `.venv/`, `node_modules/`, `dist/`, or caches.

## One-command Windows helper

V024 also includes `scripts/update_test_run.ps1` for the normal local Windows workflow. From `AI_Traffic_Light` run:

```powershell
.\scripts\update_test_run.ps1
```

It verifies the local `main` branch has no tracked edits, performs a safe `git pull --ff-only origin main`, reloads the newly pulled copy of itself, synchronizes backend/frontend dependencies, runs Python compile/structure/backend regressions, frontend typecheck/build, and `git diff --check`, then starts the backend, waits for `/health`, runs the live backend smoke automatically, starts the frontend on strict port 5173, waits for it to respond, and opens the app. It never runs `git clean` or deletes runtime data. Use `-SkipUpdate` or `-SkipTests` only when deliberately rerunning part of the workflow.
## Material color hierarchy and interface-copy refinement

V024 also refines PC Studio presentation without changing application behavior. The supplied Material 2 color-system guidance is applied as a role model rather than as a component-library conversion.

- Added explicit primary/on-primary and secondary/on-secondary roles.
- Primary blue identifies active navigation, links/focus, and dominant workflow actions.
- Secondary teal is intentionally sparse and is used for selected secondary state/progress rather than general decoration.
- Background, shell, panel, and field surfaces remain neutral and carry most screen area.
- Generic status pills are neutral; green/amber/red are now reserved for explicit success/warning/error meaning.
- The Material-derived dark `#121212` base and neutral elevation ramp are preserved.
- Added primary/secondary/danger button hierarchy and stronger tinted message containers.
- Rewrote working-page descriptions, panel titles, action labels, empty states, destructive confirmations, and explanatory notes to describe current behavior rather than historical version milestones or placeholder/setup language.
- Removed stale presentation copy such as `Confirm layout first`, old version-coded page descriptions, and the Live AI `0_2_0` note.
- Safety copy remains explicit that signal output is simulation-only; no live wheelchair/fall detection is claimed.

No endpoint, schema, signal algorithm, model format, or runtime-data format changes are introduced by this presentation refinement.
