# V026 Acceptance Checklist

V026 / `0_2_6` is the current candidate by explicit owner request. V025 / `0_2_5` is the previous unaccepted candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline. Automated checks do not promote V026.

## Release / packaging

1. `VERSION` reports `version: 0_2_6`, `previous_version: 0_2_5`, `passed_baseline: 0_2_4`, and candidate status.
2. Frontend shared project version reports only `0_2_6`.
3. `docs/PATCH_0_2_6.md` and the `CHANGELOG.md` V026 section exist.
4. Python compile, `check_structure.py`, relevant regressions, frontend typecheck/build, live smoke, and `git diff --check` pass locally.
5. Patch ZIP is changed-files-only, every member begins `AI_Traffic_Light/`, and no runtime/generated/model data is included.

## V026 two-intersection network experiment

6. At least two enabled intersections and one valid enabled directed link can be configured using the inherited V025 topology API.
7. `POST /api/traffic/network-experiments` accepts duration, density, seed, sample interval, optional profile/label/link id, and transfer share.
8. A network experiment selects exactly one valid directed source→destination link but does not change the generic N-intersection topology schema.
9. Source and destination each have a separate signal-controller runtime inside each experiment mode.
10. Fixed and Adaptive receive the same deterministic exogenous arrival plan for identical configuration/seed.
11. Repeating the same request produces repeatable scenario/Fixed/Adaptive/comparison data apart from run metadata.
12. Selected source vehicles may enter an explicit synthetic transfer pipeline after upstream service.
13. An arrived transfer event records vehicle/class, upstream departure, scheduled arrival, and delivered arrival.
14. For each arrived transfer, delivered/scheduled link arrival time reflects the configured `travel_time_seconds`.
15. Downstream transferred demand is not fabricated from a live camera source and is labeled as synthetic experiment data.
16. Fixed and Adaptive transfer outcomes may differ only because their independent source service timing differs; exogenous demand remains common.
17. Each mode exposes per-intersection vehicle/pedestrian wait, queues, throughput, signal-use, and scenario-application telemetry.
18. Network metrics expose transfer departure/arrival, transfer pipeline average/peak, corridor completion/rate, end-to-end corridor travel distribution, and aggregate vehicle wait/queue evidence.
19. Corridor travel is defined as source external arrival through downstream service, not as the configured link travel time.
20. `cooperative_control_active` remains `false`.
21. `emergency_priority_active` remains `false`.
22. Neighbour/link context does not alter ranked-scenario arbitration in V026.
23. V026 does not claim green-wave/cooperative timing merely because agents transfer between intersections.

## Network-experiment persistence / API

24. Network runs persist as bounded `netexp_*` result files under `outputs/simulation_experiments/`.
25. `GET /api/traffic/network-experiments` lists network runs without conflating them with single-junction `exp_*` runs.
26. `GET /api/traffic/network-experiments/{run_id}` retrieves one stored network run.
27. CSV export contains aligned per-intersection and network transfer/pipeline/corridor evidence and preserves `X-Request-ID`.
28. Deleting a network run removes only that `netexp_*` result.
29. Missing/disabled/invalid link selection fails with the stable network validation path and does not write a valid run.
30. Existing `/api/traffic/experiments` single-junction endpoints remain backward-compatible.

## Inherited V025 network/explanation foundation

31. Generic topology remains able to describe more than two intersections.
32. Source IDs resolve unambiguously to intersection identity; duplicate assignments remain rejected.
33. Directed links still validate endpoints, approaches, uniqueness, self-link prohibition, and travel-time bounds.
34. Network config persists atomically under ignored runtime `config/intersections.json`.
35. `/api/traffic/state` still exposes `intersection_id`, observation provenance, network context, and structured decision context.
36. Live configured links remain topology metadata and are not described as measured transfer.
37. Structured decision context still exposes scenario/observed/timing/pedestrian/vehicle/neighbour context without becoming a second controller.

## Inherited ranked scenarios / signal protection

38. Rank `1` remains highest; multiple triggered scenarios still execute only one highest-ranked eligible winner per evaluation.
39. ALL/ANY, controller-metric and zone/class conditions, missing-zone availability, persistence, cooldown, and target-phase eligibility remain functional.
40. Protected phase sequence/minimums/maximums/cycle bounds remain enforced.
41. Fixed mode performs no adaptive scenario applications.
42. Test-only accessibility/incident inputs remain explicit manual simulation inputs and do not imply perception support.
43. Signal preview remains non-mutating and history remains available.

## Inherited single-junction Simulation Lab

44. Existing Fixed-vs-Adaptive single-junction Simulation Lab remains isolated from live runtime.
45. Same-seed single-junction repeatability and zone/class scenario behavior remain intact.
46. Existing wait/queue/throughput/signal/diagnostic telemetry and `exp_*` persistence/CSV remain intact.
47. Current PC Studio Simulation Lab UI remains the single-junction experiment surface in V026; absence of a new network dashboard is not a V026 failure.

## Other inherited regression

48. V024 atomic persistence and serial polling remain intact.
49. V022 tracking/counting-line flow and V021 sampled occupancy remain distinct and functional.
50. Camera receiver/simulation, inference, zones, capture/delete/labels, training, model registry, settings, and logs show no regression.

## Claims / documentation / safety

51. `PROJECT_SCOPE.md` labels multi-intersection simulation as implemented but cooperation as still planned.
52. Documentation distinguishes exogenous arrivals, synthetic transfer events, configured link time, end-to-end corridor time, occupancy, flow, and AI detections.
53. No document claims emergency vehicle recognition, wheelchair/mobility recognition, or fall recognition without a compatible perception source.
54. V026 results are described as seeded synthetic evidence, not calibrated public-road performance or safety evidence.
55. Nothing in V026 controls or connects to physical/public-road traffic-signal infrastructure.
56. Owner explicitly confirms V026 passed before any future update changes `passed_baseline`.
