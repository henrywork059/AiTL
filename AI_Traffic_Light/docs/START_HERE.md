# Start Here — Current V022 candidate

The current candidate is V022 / `0_2_2`, explicitly requested by the owner after V021 / `0_2_1`. V021 is the previous candidate and was not separately promoted; the owner-confirmed passed baseline therefore remains V017 / `0_1_7` until explicit acceptance.

## What V022 adds

1. Load a trained model and run receiver or simulation inference.
2. Live detections receive prototype `track_id` values across consecutive frames.
3. In Zone Editor, create polygon regions as before or choose `counting_line` and click exactly two distinct points.
4. A tracked object crossing a counting line generates one directional unique-passage event for that track/line.
5. Tracked entry/exit events are generated for non-ignore polygon regions; exits include completed dwell time.
6. Traffic Analytics now has separate **Occupancy** and **Flow / Tracks** modes.
7. Flow events persist under `outputs/traffic_flow/events.jsonl`, can be filtered/plotted/exported, and can be cleared independently of occupancy history.

## Important analytics semantics

- Occupancy is still a sampled per-frame count and must not be summed into throughput.
- A V022 unique passage exists only when one stable track crosses one configured counting line.
- The tracker is lightweight class-aware centroid/IoU matching. Occlusion, abrupt motion, or crowded same-class crossings can lose/swap IDs, so the result remains prototype analytics.

## Recommended local test order

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"

& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
& $py ".\scripts\test_object_tracking_flow.py"
& $py ".\scripts\test_zone_traffic_services.py"
& $py ".\scripts\test_traffic_history_service.py"
```

Then run the complete existing `scripts/test_*.py` regression set, start the backend, run `test_backend_smoke.py`, and run frontend `npm ci`, `npm run typecheck`, and `npm run build`.

See `LOCAL_TESTING.md` and `TEST_READY_CHECKLIST.md` for the full V022 acceptance sequence.

## Safety boundary

AiTL remains a supervised local prototype. No tracking, flow, detection, or simulated traffic-light output is connected to physical/public-road traffic infrastructure.
