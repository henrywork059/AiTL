# Start Here — Current V023 candidate

The current candidate is V023 / `0_2_3`. V022 / `0_2_2` is the owner-confirmed passed baseline.

## What V023 adds

1. Traffic Logic now manages a persistent user-defined simulated signal policy.
2. Normal Timing edits min/base/max values for all six protected phase slots.
3. Fixed mode uses normal timing only; Adaptive mode applies bounded live-demand rules; Test mode additionally accepts explicit manual accessibility/incident inputs.
4. Rule priority, persistence/hysteresis, cooldowns, demand memory, stale-data fallback, phase/cycle caps, pending demand and minimum service are visible/auditable.
5. Protected phase order remains vehicle green → yellow → all-red → pedestrian WALK → CLEAR → all-red.
6. Test-mode incident input produces simulated all-red hold until explicitly cleared.
7. Preview scenarios and dry-run evaluate rules without unsafe arbitrary phase jumps.
8. Signal decision history persists under `outputs/signal_rules/` and is independent of occupancy/flow histories.

V023 inherits accepted V022 cross-frame tracking/counting-line flow and V021 occupancy analytics. Occupancy and flow remain separate metrics.

## Recommended local test order

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
& $py ".\scripts\test_signal_rules_service.py"
```

Then run the complete non-live `scripts/test_*.py` regression set, start the backend, run `test_backend_smoke.py`, and run frontend `npm ci`, `npm run typecheck`, and `npm run build`.

See `LOCAL_TESTING.md` and `TEST_READY_CHECKLIST.md` for the full V023 acceptance sequence.

## Perception limitation

The current model is not claimed to detect wheelchairs/mobility assistance or falls. Those conditions are explicit Test-mode inputs until a compatible perception source is deliberately added.

## Safety boundary

AiTL remains a supervised local simulation/computer-vision prototype. No signal rule, timing adjustment, detection, tracking, or analytics output is connected to physical/public-road traffic infrastructure.
