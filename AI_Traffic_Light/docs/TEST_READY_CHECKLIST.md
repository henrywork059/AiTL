# V022 acceptance checklist

V022 / `0_2_2` is the current candidate. V021 / `0_2_1` is the previous candidate, and the owner-confirmed passed baseline remains V017 / `0_1_7`. Automated tests do not promote `passed_baseline`.

## Release/instruction integrity

1. `VERSION` reports `version: 0_2_2`, candidate status, `previous_version: 0_2_1`, and `passed_baseline: 0_1_7`.
2. `python scripts/check_structure.py` passes in the complete repository.
3. Backend health/smoke/template surfaces all derive/report `0_2_2` from root `VERSION`.
4. Frontend shared project version/reporting surfaces show `0_2_2` without unrelated hard-coded release literals.
5. V022 has `docs/PATCH_0_2_2.md`, synchronized changelog/docs, and updated agent rules.
6. Final changed-files ZIP passes `scripts/validate_patch_zip.py`, matches the intended manifest, and excludes runtime/generated/model data.

## Cross-frame tracking

7. Supported vehicle/person detections receive prototype `track_id` values.
8. A clearly moving object normally retains the same track ID across consecutive matched frames.
9. Tracker processing is frame-deduplicated so multiple calls for the same source/frame/timestamp do not create duplicate events.
10. Missing tracks expire after the configured bounded tolerance rather than remaining active forever.
11. Loading/unloading/changing inference model resets active tracking identity without deleting persisted flow events.
12. Live AI can display track ID beside the detection label.
13. Tracking status exposes active track totals and current track summaries.

## Counting lines and unique passage events

14. `counting_line` is accepted by backend/schema/frontend and requires exactly two distinct points.
15. Counting lines persist through the existing zone storage and render as lines in Zone Editor/Live AI.
16. Counting lines remain analytics-only and do not alter signal/recommendation rules.
17. A matched track crossing a line generates one `line_crossing` event.
18. One track is counted at most once for a given line during that track lifetime, preventing boundary jitter from repeatedly incrementing it.
19. The same track may be counted once on each of multiple different lines.
20. Line event records include track ID, class, class group, direction, timestamp/source-frame context, and line identity.
21. Direction is one of left-to-right, right-to-left, top-to-bottom, or bottom-to-top according to dominant track motion.
22. Unique vehicle/person passage totals are derived only from `line_crossing` events, never by summing occupancy samples.

## Region events and dwell

23. Existing non-ignore polygon regions generate `region_entry` and `region_exit` track events.
24. Region exit includes non-negative dwell time from the corresponding tracked entry.
25. `pedestrian_waiting` exit dwell contributes to the prototype average pedestrian waiting-time summary.
26. Region filters/summaries distinguish entries, exits, and average dwell from counting-line passages.
27. Counting lines do not appear as V021 occupancy-region scopes.

## Persistent flow analytics

28. Flow events persist in bounded JSONL runtime storage under `outputs/traffic_flow/`.
29. Flow queries support time, line, region, and class filters.
30. Flow response includes timestamp-aware per-minute buckets and summary totals.
31. Traffic Analytics keeps distinct **Occupancy** and **Flow / Tracks** modes with clearly different semantics.
32. Flow mode shows unique vehicle/person passages, region entries/exits, dwell/wait metrics, direction totals, and recent events.
33. Flow CSV exports selected flow events and includes `X-Request-ID`.
34. Clear flow requires explicit frontend confirmation and removes only flow-event history, not occupancy history, captures, labels, zones, settings, models, or training output.
35. Persisted flow events survive backend restart; active track identity does not claim continuity across restart.
36. `outputs/traffic_flow/` is runtime data and absent from source patch ZIPs.

## V021/V020/V017 regression

37. V021 sampled whole-frame/region occupancy analytics still work and remain described as occupancy, not unique throughput.
38. V021 signal-aware vehicles/pedestrians still obey simulated signal phases/stop lines/crosswalk behavior.
39. Simulation pause freezes scene/signal; density controls still work.
40. Active simulator signal and detection recommendation remain separate/auditable in simulation mode.
41. Camera receiver, camera-backed Zone Editor, saved-zone overlay, and Show zones show no regression.
42. Capture/delete/manual-label/managed-dataset lifecycle shows no regression.
43. Training convergence/patience early stopping and model registry/load/default/delete show no regression.
44. Settings, logs, confidence controls, and request-ID/error-envelope behavior show no regression.

## Validation and safety

45. Python compile checks and all relevant backend service/API regressions pass using the local backend `.venv`.
46. `scripts/test_object_tracking_flow.py`, `scripts/test_traffic_history_service.py`, and `scripts/test_zone_traffic_services.py` pass.
47. Live `scripts/test_backend_smoke.py` passes and checks occupancy/tracks/flow APIs plus both CSV exports without clearing runtime history.
48. Frontend `npm ci`, `npm run typecheck`, and `npm run build` pass.
49. `git diff --check` passes in the complete Git repository.
50. The tracker limitation is visible/documented: it can lose/swap identity under occlusion, abrupt movement, or detection gaps and is not certified traffic measurement.
51. Nothing in V022 connects detections, tracks, analytics, or recommendations to physical/public-road signal infrastructure.
52. The owner completes manual/UI checks and explicitly says V022 passed before `passed_baseline` is changed to `0_2_2`.
