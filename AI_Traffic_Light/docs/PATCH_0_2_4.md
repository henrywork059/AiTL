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
