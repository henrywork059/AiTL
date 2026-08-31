# Patch 0_3_9 — Idempotent update / test / run workflow

V039 / `0_3_9` is the current unaccepted candidate after V038. `passed_baseline` remains `0_2_4`.

## Why V039 exists

The normal Windows helper previously stopped after a successful regression run whenever an older PC Studio backend or frontend was still listening on ports 8000 or 5173. That forced a separate manual process-kill step and meant the same update/test/run command was not reliably reusable.

V039 changes only the local Windows development workflow so one normal command can update, validate, safely replace an existing AiTL PC Studio instance, and relaunch it.

## Implemented

- `scripts/update_test_run.ps1` remains fast-forward-only on local `main` and still refuses tracked local edits before updating.
- After pulling, the helper reloads itself from disk so the newly pulled workflow owns the rest of the run.
- Dependency refresh, Python compile, structure validation, backend regressions, frontend typecheck/build, Git whitespace/cleanliness checks, health readiness, live backend smoke and strict-port startup remain part of the normal run.
- Before startup, ports 8000 and 5173 are inspected for existing listeners.
- A listener is stopped automatically only when Win32 process executable/command-line evidence identifies it as belonging to this AiTL repository's PC Studio backend/frontend process tree.
- Child processes belonging to the same AiTL process tree are terminated so stale Uvicorn/Vite reload children do not keep a port occupied.
- If an unrelated process owns either port, the helper refuses to terminate it and reports a safety error instead.
- Runtime/user data remains untouched; the helper still never uses `git clean` or destructive repository cleanup.
- Added regression coverage for idempotent AiTL restart ownership checks and unrelated-port protection.

## Canonical command

The same command can be used for routine update, validation and launch from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Optional `-SkipUpdate` and `-SkipTests` remain available for deliberate local workflows, but are not required for normal use.

## Deliberate non-changes

- V038/R10 Camera Diagnostics functionality is unchanged.
- ESP production/diagnostic firmware and camera wire protocols are unchanged by V039.
- Backend API envelopes, error codes and signal-policy behavior are unchanged.
- Dataset, training, inference, simulation, multi-intersection experiment and runtime-data semantics are unchanged.
- No physical/public-road signal-control authority is introduced.
- `passed_baseline` remains `0_2_4`; V039 must not be promoted without explicit owner acceptance.

## Acceptance target

Run the canonical command while an older AiTL PC Studio instance is already running. The helper should update and validate the repository, identify and stop only the old AiTL-owned listeners, start the new backend/frontend, pass live smoke, and open PC Studio without a manual port-kill step. An unrelated process on 8000 or 5173 must still block startup rather than being killed automatically.
