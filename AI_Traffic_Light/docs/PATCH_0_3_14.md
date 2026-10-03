# Patch 0_3_14 — Frontend polling reliability and code optimization

V0314 / `0_3_14` is the owner-requested whole-project code-audit and reliability candidate after unaccepted V0313. `0_3_11` remains the owner-confirmed passed baseline until explicit V0314 acceptance.

## Audit result

The audit reviewed the current release state, Windows update/test/run path, backend route ownership, major backend service hotspots, frontend periodic work, release guards, and existing regression coverage.

No evidence justified reconstructing the backend signal controller, network simulation, camera transport, persistence, dataset, training, or inference services in this patch. Those modules remain intact to avoid changing tested safety or data semantics without a concrete failure.

The verified cross-project defect was periodic asynchronous React work still using `window.setInterval`. A slow request could overlap the next tick and accumulate concurrent requests even though the project already provides `useSerialPolling` for settled-task scheduling.

## Implemented

Six remaining periodic pages now use the existing shared serial polling hook:

- Camera Diagnostics progress;
- Dataset Capture status;
- Live AI inference status;
- Logs;
- Traffic Analytics;
- Train / Export status.

`TrafficAnalyticsPage` uses the hook's new `restartKey` option so mode/filter changes still trigger an immediate refresh while periodic requests remain non-overlapping.

Live AI now converts initial inference-status failure into page error state instead of an unhandled promise rejection. Dataset and training status polling also route failures through existing page error/message state, and Train / Export handles runtime-settings load failure explicitly.

## Regression hardening

`scripts/check_structure.py` now:

- lists every known periodic serial-polling surface;
- requires those surfaces to use `useSerialPolling`;
- recursively rejects `window.setInterval` anywhere under frontend TypeScript/TSX source.

`scripts/test_frontend_polling_structure.py` validates the shared hook and all registered periodic surfaces from the same source-of-truth list.

## Compatibility

V0314 does not change:

- HTTP endpoints, response envelopes, request IDs, or stable error codes;
- backend route/service ownership or persisted JSON schemas;
- traffic signal arbitration, protected transitions, network policy priority, or simulation semantics;
- camera APIs, V0310 production ESP32-CAM `ATL1` transport, or diagnostic firmware;
- dataset capture format, labels, training/inference contracts, or model registry;
- the single-selected-source live observation boundary;
- the prototype-only/no-public-road-control safety boundary.

## Acceptance target

Run:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Confirm all automatic regressions, frontend typecheck/build and live backend smoke pass. Then exercise Camera Diagnostics, Dataset Capture, Live AI, Logs, Traffic Analytics and Train / Export long enough to confirm polling remains responsive and does not create duplicated requests or stale UI state.

`0_3_11` remains the passed baseline until the owner explicitly confirms V0314 PASS.
