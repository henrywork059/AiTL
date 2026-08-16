# Start Here — Current V024 candidate

The current candidate is V024 / `0_2_4`. V023 / `0_2_3` is the previous candidate; V022 / `0_2_2` remains the owner-confirmed passed baseline because V023 was not explicitly accepted.

## What V024 hardens

- shared atomic JSON replacement for runtime settings, zones, and model-registry metadata;
- synchronized zone writes and model-registry state transitions;
- non-overlapping App-level camera/live-context polling through `useSerialPolling`;
- architecture and regression checks that protect those maintenance boundaries;
- no API, signal-semantic, dataset/model-format, or design-system changes.

## Inherited V023 capabilities

V023 inherits accepted V022 cross-frame tracking/counting-line flow and V021 occupancy analytics. Occupancy and flow remain separate metrics.

## Recommended local test order

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
& $py ".\scripts\test_atomic_json_store.py"
& $py ".\scripts\test_frontend_polling_structure.py"
& $py ".\scripts\test_signal_rules_service.py"
```

Then run the complete non-live `scripts/test_*.py` regression set, start the backend, run `test_backend_smoke.py`, and run frontend `npm ci`, `npm run typecheck`, and `npm run build`.

See `LOCAL_TESTING.md` and `TEST_READY_CHECKLIST.md` for the full V024 acceptance sequence, including inherited V023 behavior checks.

## Perception limitation

The current model is not claimed to detect wheelchairs/mobility assistance or falls. Those conditions are explicit Test-mode inputs until a compatible perception source is deliberately added.

## Safety boundary

AiTL remains a supervised local simulation/computer-vision prototype. No signal rule, timing adjustment, detection, tracking, or analytics output is connected to physical/public-road traffic infrastructure.
