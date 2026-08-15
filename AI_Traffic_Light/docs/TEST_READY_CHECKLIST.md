# V021 acceptance checklist

V021 / `0_2_1` is the current candidate. V020 / `0_2_0` is the previous candidate, and the owner-confirmed passed baseline remains V017 / `0_1_7`. Automated tests do not promote `passed_baseline`.

## Release/instruction integrity

1. `VERSION` reports `version: 0_2_1`, candidate status, `previous_version: 0_2_0`, and `passed_baseline: 0_1_7`.
2. `python scripts/check_structure.py` passes in the complete repository.
3. Backend FastAPI, health, smoke, and template version surfaces all derive/report `0_2_1` consistently.
4. Dashboard Project stage, sidebar/version label, and frontend fallback version surfaces report `0_2_1`.
5. `AGENTS.md`, `docs/AI_AGENT_GUIDE.md`, and `docs/AI_AGENT_CHECKLIST.md` describe the candidate/baseline gate and runtime-data preservation rules.
6. The final ZIP passes `scripts/validate_patch_zip.py`, contains only intended changed files, and has no runtime/generated/model content.

## Existing V020 feature checks

7. Existing V016/V017 camera simulation, training convergence, early stopping, settings, logs, traffic logic, labeling, and model-management functions show no regression.
8. Zone Editor displays the current receiver or simulation camera frame rather than the old drawn reference background.
9. Zone click coordinates stay aligned with the camera image and save through the existing 1280×720 reference coordinate system.
10. Saved zones persist across page navigation/backend requests.
11. Live AI overlays persisted zone polygons over real receiver/simulation camera frames.
12. Zone overlays scale correctly if the active camera resolution differs from 1280×720.
13. Live AI **Show zones** toggle hides/shows zones without changing inference results.
14. A compact traffic signal appears at the top-right of the Live AI canvas.
15. The compact signal reflects the current simulation-only phase and does not imply physical traffic control.
16. Dataset Capture can delete the latest saved capture after confirmation.
17. Dataset Review can delete the selected saved capture after confirmation.
18. Deleting a capture removes its image file, paired metadata JSON, and saved manual-label JSON when present.
19. Deleted captures disappear from the review list and capture counts update.
20. Deleting a capture used by an existing managed YOLO build makes that build stale until rebuilt.
21. Re-deleting a missing capture returns `ATL-DATASET-003`; filesystem deletion failures use `ATL-DATASET-007`.
22. Delete responses preserve the standard JSON envelope, request ID, and backend logging.


## Traffic occupancy analytics and counting regions

23. `counting_region` is accepted by backend validation/schema and can be created/saved/reloaded from the camera-aligned Zone Editor.
24. Multiple counting regions may coexist/overlap and remain analytics-only; they do not alter the simulation recommendation rules.
25. `GET /api/traffic/state` returns detection-backed whole-frame pedestrian/vehicle totals and per-region pedestrian/vehicle/total counts.
26. Traffic history records timestamped, deduplicated detection-backed samples while the backend runs and does not manufacture zero samples when camera/model inference is unavailable.
27. Traffic Analytics plots pedestrian and vehicle occupancy over selectable time windows for Whole frame or a selected region.
28. Analytics shows average/peak counts with peak times, busiest-region context, and simulation phase-change context.
29. CSV export returns the selected history scope with `X-Request-ID`.
30. Clear history requires frontend confirmation and resets only traffic-history runtime data, not captures, labels, zones, settings, models, or training outputs; recording may resume on the next valid detection sample.
31. UI/docs clearly state that history is sampled occupancy, not unique passage/throughput counting.
32. `outputs/traffic_history/` remains runtime data and is absent from the source patch ZIP.

## Validation and safety

33. Python compile checks and relevant backend service/API/regression tests pass locally using the backend `.venv`.
34. `scripts/test_backend_smoke.py` confirms `meta.request_id` and root-version agreement for version endpoints.
35. Frontend `npm run typecheck` and `npm run build` pass.
36. `git diff --check` passes in the complete repository.
37. The intended changed-file manifest matches the ZIP manifest and SHA-256 is recorded.
38. Live detections/traffic recommendations remain disconnected from physical public-road traffic signals.
39. The owner completes UI/manual checks and explicitly says V021 passed before `passed_baseline` is changed to `0_2_1`.
