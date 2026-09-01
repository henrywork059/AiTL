# Patch 0_3_12 — Repository cleanup and runner hardening

V0312 / `0_3_12` is a cleanup candidate created at the owner's explicit request. `0_3_11` remains the owner-confirmed passed baseline until explicit acceptance of V0312.

## Purpose

Reduce obsolete repository surface and make the normal Windows workflow easier to maintain without changing the accepted application behavior.

## Cleanup

Removed superseded artifacts that were no longer part of the active workflow:

- old root-level `PATCH_MANIFEST_*` and `PATCH_APPLY_INSTRUCTIONS_*` distribution files;
- V010 Windows test-ready instructions;
- the V036 tracked-metadata finalizer and the regression whose only purpose was preserving it;
- duplicate generic backend/frontend Windows launch wrappers and the old smoke-test `.bat` wrapper;
- the archived standalone V036 Arduino firmware/example and its historical structural regression.

Retained intentionally:

- historical `docs/PATCH_*` release records and `CHANGELOG.md` history;
- V0310 production ESP32-CAM firmware;
- V037 source because the V0310 Arduino/PlatformIO production wrappers still inherit it;
- R9/R10 and transport diagnostic firmware/tools;
- `setup_backend_windows.ps1` for first-time/recovery environment setup;
- all current PC Studio APIs, data/training/inference, Junction Network, simulation and signal-control prototype behavior.

The root README is now version-agnostic and points release-state questions to `VERSION` instead of duplicating a stale release snapshot.

## Windows runner repair

A real Windows run exposed a recursive reload bug: after `git pull`, the self-reloaded script did not bind the array-splatted `-SkipUpdate` switch and repeatedly pulled/reloaded itself.

V0312 replaces that invocation with explicit switch binding:

```powershell
& $PSCommandPath -SkipUpdate -SkipTests:$SkipTests -RefreshDependencies:$RefreshDependencies
```

It also adds `AITL_RUNNER_RELOADED` as a one-reload guard. If a future PowerShell parameter-binding regression occurs, the runner fails once with `Recursive update prevented` instead of entering an unbounded loop.

The existing safeguards remain:

- fast-forward-only `origin/main` update;
- tracked local edits block automatic update;
- untracked runtime/user data is preserved;
- dependency refresh remains Git-change-aware with `-RefreshDependencies` recovery;
- automatic offline regressions, frontend typecheck/build, Git cleanliness and live smoke remain in the normal workflow;
- only AiTL-owned PC Studio process trees on ports 8000/5173 may be terminated automatically;
- unrelated port owners remain protected.

## Behavior intentionally unchanged

V0312 does not change:

- API envelopes, request IDs or stable error behavior;
- live inference/training/dataset contracts;
- Junction Network semantics or single-selected-source live pipeline boundary;
- simulation or adaptive signal rules;
- V0310 production camera protocol/transport;
- physical/public-road safety boundary.

## Acceptance target

Run the normal command from any PowerShell directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The command must perform at most one update/reload cycle, then continue through compile/structure/regressions/frontend checks/live smoke and start PC Studio. Re-running it while PC Studio is already running must safely replace only AiTL-owned listeners.

`0_3_11` remains the passed baseline until the owner explicitly confirms V0312 passes.
