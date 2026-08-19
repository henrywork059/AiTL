# V025 acceptance checklist

V025 / `0_2_5` is the current candidate. V024 / `0_2_4` is the previous version and owner-confirmed passed baseline. Automated tests do not promote V025.

## Release / packaging

1. `VERSION` reports `version: 0_2_5`, `previous_version: 0_2_4`, `passed_baseline: 0_2_4`, and candidate status.
2. `check_structure.py`, Python compilation, backend regression tests, frontend typecheck/build, live smoke, and `git diff --check` pass locally.
3. Patch ZIP is changed-files-only, all members start `AI_Traffic_Light/`, validator passes, and no runtime/generated/model files are present.

## Ranked scenario configuration

4. Traffic Logic tabs are Live Decision / Signal Timing / Scenario Rules / Test & Safety / History.
5. A scenario can be added, duplicated, deleted, enabled/disabled, renamed, and assigned an explicit numeric rank.
6. Rank `1` is highest and saved ranks are unique within each profile; duplicate ranks are rejected.
7. A scenario supports 1–8 conditions and ALL/ANY matching.
8. A condition can use a controller metric.
9. A condition can use one selected polygon zone plus detected class name and comparison threshold.
10. Zone/class condition supports `*` for all detected classes in the selected zone.
11. Supported comparisons are `>`, `>=`, `<`, `<=`, and `=`.
12. Invalid scenario ids, ranks, conditions, operators, actions, target phases, or timing values are rejected with the existing traffic-rule error path and do not replace the last valid config.
13. Older saved V023/V024 config with legacy `rules` and no `scenarios` loads through deterministic migration into editable scenarios.
14. An explicitly saved empty `scenarios` list remains empty rather than being silently repopulated.

## Arbitration

15. Multiple scenarios can be triggered at the same time.
16. Only one highest-ranked **eligible** scenario executes in one evaluation.
17. The winning scenario is exposed by id/label and appears as `winner` in live status.
18. Lower-ranked eligible triggered scenarios are suppressed with an explanation naming the higher-ranked winner.
19. Disabled scenarios do not enter arbitration.
20. A scenario referencing a missing/deleted zone is `unavailable` and does not block the next eligible scenario.
21. A scenario whose required condition source is unavailable is explained rather than silently using a false positive value.
22. A triggered scenario whose target-phase list excludes the current phase is suppressed and does not block the next eligible scenario.
23. A triggered scenario still inside cooldown is suppressed and does not block the next eligible scenario.
24. Persistence prevents a transient condition from winning before its configured stable interval.
25. Scenario status shows observed condition values, threshold/operator, matched flag, and reason.

## Signal response / guards

26. Scenario actions support extend, reduce, hold, request-next-protected-phase, and Test-mode incident hold.
27. Optional requested service can be none, pedestrian, or vehicle; request-next requires pedestrian/vehicle service.
28. Scenario action executes only in checked target phases.
29. No scenario reduction goes below protected minimum or already-served time.
30. Extensions remain bounded by phase maximum and maximum-cycle policy.
31. Request-next shortens only within protected bounds and does not directly jump between conflicting movements.
32. Protected sequence remains vehicle green → yellow → all-red → pedestrian WALK → pedestrian CLEAR → all-red.
33. Fixed mode executes no adaptive scenarios.
34. Adaptive mode uses fresh live observations and falls back to configured normal timing when stale/unavailable.
35. Demand memory still applies to controller metrics; zone/class counts remain per-frame observations.
36. Test mode additionally permits explicit mobility/incident flags without claiming live perception capability.
37. Incident hold/recovery remains simulation-only and resumes safely from a protected phase.

## Traffic observation extension

38. `GET /api/traffic/state` includes `zone_class_counts` for every countable polygon zone.
39. Existing countable zone with no detections appears with an empty class-count object.
40. Arbitrary detector classes can appear in `zone_class_counts` even when they are not pedestrian/vehicle occupancy groups.
41. Ignore zones exclude detections from scenario zone/class counts.
42. Counting lines remain analytics-only and are not zone/class scenario polygons.
43. UI/docs describe zone/class counts as sampled per-frame observations, not throughput.

## Traffic Logic presentation

44. Scenario Rules uses a scenario list plus selected-scenario editor instead of expanding every scenario into one long page.
45. Scenario editor groups identity/rank, trigger conditions, response, protected target phases, and stability guards.
46. Live Decision shows the current winner and compact rank-ordered arbitration states.
47. Live zone/class cards expose current values available to conditions.
48. Scenario page polling uses the serial polling helper rather than overlapping `setInterval` requests.
49. Light/dark styling uses shared design-system tokens and no page-local hex/gradient treatment.

## Simulation Lab integration / repeatability

50. Simulation Lab remains an isolated Fixed-vs-Adaptive experiment surface and does not reset the live camera/controller runtime.
51. An experiment snapshots configured zones and generates synthetic per-zone/per-class observations for scenario evaluation.
52. Identical density/profile/duration/seed/sample interval and zone/config snapshot produce repeatable Fixed/Adaptive/comparison telemetry apart from run metadata.
53. Fixed experiment records zero adaptive scenario applications.
54. A suitable zone-based scenario can appear in Adaptive scenario-application telemetry.
55. Vehicle/pedestrian wait distributions, queue pressure, throughput, phase utilization, clearance, extension/reduction and conflict diagnostic remain available.
56. Simulation Lab remains one grouped page with Summary / Waiting & queues / Throughput / Signal behavior / Raw samples tabs and bounded raw-data pagination.
57. Experiment persistence/list/get/delete/CSV remains under `outputs/simulation_experiments/`; deletion removes only that experiment.

## Inherited V024/V022/V021 regression / safety

58. V024 atomic persistence, zone/model-registry synchronization and App-level serial polling remain intact.
59. V022 tracking/counting-line flow and V021 occupancy remain separate and functional.
60. Camera simulation/receiver, zones, capture/delete/labels, training, inference/model registry, settings and logs show no regression.
61. Current YOLO is not claimed to detect wheelchairs/mobility assistance or falls.
62. Experiment results are seeded synthetic simulation evidence only, not a claim Adaptive is universally better.
63. Nothing in V025 controls or connects to physical/public-road traffic-signal infrastructure.
64. Owner completes manual/UI checks and explicitly confirms V025 passed before `passed_baseline` changes.
