# Patch 0_3_15 — Concurrency hardening and conflict cleanup

V0315 / `0_3_15` is the next candidate after unaccepted V0314. `0_3_11` remains the owner-confirmed passed baseline.

## Audit findings

The follow-up audit focused on internal conflicts, concurrency, duplicate paths and apparently redundant files.

Verified active compatibility code was retained:

- PlatformIO compiles only `main_v0310.cpp`; it intentionally textually includes the V037 implementation.
- The V0310 Arduino sketch intentionally reuses the adjacent V037 sketch.
- `mockData.ts` remains an API fallback dependency.
- `experimentApi.ts` remains the Simulation Lab API owner.
- camera diagnostic helper modules remain wired through the enhanced diagnostic service.

The concrete instability was frontend request ownership. V0314 prevented timer-to-timer overlap, but an in-flight request could still collide with an effect restart, explicit Refresh action, or a mutation that reads/writes the same state.

## Implemented

### Shared single-flight polling

`useSerialPolling` now owns one in-flight promise per polling surface.

- timer ticks reuse an active request instead of starting another;
- effect restarts wait for old work to settle before executing the latest query;
- React StrictMode effect replay cannot create concurrent duplicate requests;
- callers can use `runNow()` for manual refresh through the same single-flight path;
- callers can use `waitForIdle()` before state-changing operations;
- synchronous task/error-handler failures still clear the single-flight state.

### Conflict cleanup

- **Live AI:** removed the separate custom detection `setTimeout` loop; detection polling now uses the shared polling owner.
- **Logs:** manual Refresh now reuses the same in-flight request as periodic polling.
- **Dataset Capture:** capture/delete pause polling, drain any active status read, perform the mutation, then refresh through the shared owner.
- **Traffic Analytics:** manual refresh and post-clear refresh reuse the polling owner; clear waits for an active analytics read and pauses periodic polling while deleting history.
- **Train / Export:** training start waits for any active training-status read and pauses status polling during start.
- **Camera mode:** simulation/physical-mode switching waits for active camera-status polling and pauses new camera-status polling during the mode change.

## Regression hardening

The frontend polling regression now checks:

- single-flight state and controller methods in the shared hook;
- all registered periodic polling surfaces;
- removal of the Live AI custom detection timer;
- manual-refresh routing for Logs and Traffic Analytics;
- mutation/status serialization for Dataset Capture, Traffic Analytics, Train / Export and camera mode switching.

The structural validator now requires the shared polling hook to retain the single-flight operations.

## Compatibility

No changes were made to:

- backend HTTP endpoints, envelopes, request IDs or stable error codes;
- persisted configuration/data schemas;
- signal arbitration, protected transitions or network policy;
- simulation experiment behavior;
- ESP32-CAM production firmware/wire protocol;
- dataset formats, labels, training/inference/model contracts;
- the single-selected-source live observation boundary;
- prototype/public-road safety boundaries.

## Acceptance

Run:

```powershell
& "C:\Users\henry_sik0ar\Downloads\AiTL_app\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Then stress the affected pages by changing filters/modes and clicking manual actions while periodic refresh is active. There should be no duplicate request bursts, stale state returning after a mutation, or polling that permanently stops after an error.

`0_3_11` remains the passed baseline until explicit V0315 PASS.
