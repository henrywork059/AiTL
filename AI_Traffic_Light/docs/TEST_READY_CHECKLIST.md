# V027 Acceptance Checklist

V027 / `0_2_7` is the current candidate by explicit owner request. V026 / `0_2_6` is the previous unaccepted candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline. Automated checks do not promote V027.

## Release / packaging

1. `VERSION` reports `0_2_7`, previous `0_2_6`, passed baseline `0_2_4`, and candidate status.
2. `docs/PATCH_0_2_7.md` and a V027 changelog section exist.
3. Changed-files ZIP contains only `AI_Traffic_Light/` paths and excludes runtime/generated data.
4. Python compile, structure checks, relevant regressions, frontend typecheck/build, live smoke, `git diff --check`, and ZIP validation pass locally.

## Three-mode network experiment

5. `POST /api/traffic/network-experiments` accepts Fixed/Adaptive/Cooperative comparison parameters through one request.
6. Same seed/config produces the same exogenous arrival-plan fingerprint across repeated runs.
7. Fixed, Independent Adaptive and Cooperative Adaptive each have separate A/B experiment runtime state.
8. Synthetic transfer timing remains explicit and deterministic over the selected configured link.
9. Fixed and Adaptive report cooperation inactive; Cooperative reports cooperation active.
10. Existing backward-compatible `comparison` still represents Adaptive vs Fixed.
11. `comparisons` additionally contains Adaptive vs Fixed, Cooperative vs Fixed, and Cooperative vs Adaptive.

## Cooperation behavior

12. Cooperative mode derives predicted incoming demand only from synthetic transfers already in the configured-link pipeline.
13. Lookahead, max-extension and minimum-incoming settings are snapshotted in the result.
14. Downstream vehicle green may be extended only within saved phase maximum and maximum-cycle caps.
15. Cooperation never reorders or skips the protected phase sequence.
16. Earlier vehicle preparation may reduce only the current protected phase toward its configured minimum.
17. Active pedestrian demand blocks cooperation-driven shortening of pedestrian WALK/CLEAR.
18. Coordination events record deterministic coordination ID, link/source/destination identity, provenance, time, pre-advisory destination phase, incoming count, earliest ETA, action, reason, applied flag and timing delta.
19. Coordination telemetry records evaluations, triggers, applied advisories, green extensions, progression requests, pedestrian protections, and timing seconds added/reduced.
20. Cooperation provenance is explicitly synthetic predicted-arrival evidence.
21. No test requires Cooperative to outperform Independent Adaptive universally.

## Persistence / API / CSV

22. `netexp_*` list/get/delete remains functional.
23. JSON responses preserve standard envelopes/request IDs.
24. CSV export preserves `X-Request-ID`.
25. CSV includes aligned Fixed, Adaptive and Cooperative source/destination/network fields plus cooperative coordination columns.
26. Deleting a network run does not remove single-junction runs or other runtime/user data.

## Validation / negative paths

27. Invalid/missing selected link is rejected with the existing network validation error path.
28. Cooperation lookahead outside 1-60 seconds is rejected.
29. Cooperation max extension outside 0-20 seconds is rejected.
30. Cooperation minimum incoming count outside 1-20 is rejected.

## Inherited signal/network invariants

31. V026 independent network transfer semantics remain available inside Fixed/Adaptive results.
32. V025 ranked scenario one-winner arbitration remains intact.
33. Protected phase minimum/maximum/cycle constraints remain controller-owned.
34. Single-junction Simulation Lab remains unchanged and isolated from live runtime.
35. Live configured network links remain topology metadata rather than observed cross-camera flow.
36. Existing occupancy, flow/tracking, dataset/training/inference/model/settings/logging features show no regression.

## Claims / safety

37. V027 is described as isolated synthetic two-intersection cooperation, not general live N-intersection cooperation.
38. Configured travel time is described as a simulation input, not a measured/learned road estimate.
39. In the retained V027 Fixed/Adaptive/Cooperative modes, emergency priority remains inactive.
40. No unsupported emergency/wheelchair/fall perception claim is introduced.
41. Nothing controls or connects to physical/public-road traffic-signal infrastructure.
42. Owner explicitly confirms V027 passed before `passed_baseline` changes.


## V028 pedestrian-aware cooperative acceptance

43. `VERSION` reports `0_2_8`, previous `0_2_7`, passed baseline `0_2_4`.
44. Focused V028 pedestrian-aware network regression passes.
45. Fixed / Adaptive / Cooperative / Pedestrian-aware Cooperative share one seeded exogenous demand fingerprint.
46. V027 cooperation still produces bounded predicted-arrival coordination evidence.
47. Oldest pedestrian wait and request lifecycle/service-session metrics are present.
48. A request at/above `pedestrian_max_wait_seconds` can trigger bounded protected progression toward pedestrian service without violating phase minimums.
49. Served synthetic pedestrians produce crossing occupancy for the configured clearance interval.
50. Active crossing occupancy can reserve bounded WALK/CLEAR time within phase/cycle maxima.
51. Neighbour coordination does not shorten pedestrian WALK/CLEAR while waiting or crossing demand is active.
52. Pedestrian-aware vs Cooperative comparison includes pedestrian wait/queue/max-wait metrics.
53. Four-mode CSV contains pedestrian-awareness evidence columns.
54. In the retained V028 pre-emergency modes, emergency priority remains inactive and no public-road control claim is introduced.
55. Full inherited regression, structure check, frontend typecheck/build and live smoke pass locally before owner acceptance.

## V029 simulated emergency-priority acceptance

56. `VERSION` reports `0_2_9`, previous `0_2_8`, passed baseline `0_2_4`, candidate status.
57. `docs/PATCH_0_2_9.md` and a V029 changelog section exist.
58. Retained V027 cooperation, retained V028 pedestrian-aware, and focused V029 emergency regressions pass.
59. Current network `scenario.comparison` retains the V029 emergency baseline/priority pair; later candidates may add modes before that pair.
60. `emergency_baseline_cooperative` and `emergency_priority_cooperative` receive identical configured emergency event objects and the same seeded base arrival plan.
61. Emergency event contains ID/type/vehicle/source/destination/link/activation fields with `simulated_configured_emergency_event` provenance, null confidence, and `detector_claimed: false`.
62. Baseline emergency mode carries the event but reports emergency timing priority inactive/zero.
63. Priority mode can record source priority, downstream preparation, and destination priority roles without creating a second phase state machine.
64. Emergency priority may extend current vehicle green only within phase maximum, maximum-cycle cap, and emergency extension cap.
65. Emergency protected progression reduces only the current phase toward its configured minimum and never skips protected phase order.
66. Active simulated pedestrian crossing occupancy yields an explicit emergency priority denial until clearance.
67. Emergency lifecycle evidence records activation, source departure, downstream arrival, and—when completed during the run—clear plus recovery.
68. Emergency metrics expose event status, source/destination wait, total travel, priority evaluations/grants/denials/applications, downstream preparations, and timing seconds added/reduced.
69. `comparisons.emergency_priority_vs_emergency_baseline` exists; emergency delay/travel deltas are available only when the event completes in both matched modes.
70. Six-mode CSV includes emergency status/role/decision/action/ETA/applied columns and preserves `X-Request-ID`.
71. Invalid event time/type/lookahead/extension inputs are rejected by request/service validation.
72. V029 is described only as simulated/configured emergency priority; no live detector, hardware/public-road pre-emption, safety-interlock bypass, or safety-certification claim is introduced.
73. Full inherited backend/frontend/structure/live-smoke/`git diff --check` validation passes locally before owner acceptance.
74. Owner explicitly confirms V029 passed before `passed_baseline` changes.

## V030 vehicle-class-aware acceptance

76. `VERSION` reports `0_3_0`, previous `0_2_9`, passed baseline `0_2_4`, candidate status.
77. `docs/PATCH_0_3_0.md` and a V030 changelog section exist.
78. Retained V027 cooperation, V028 pedestrian-aware, V029 emergency-priority, and V030 vehicle-class-aware focused regressions pass.
79. `scenario.comparison` contains seven documented modes including `class_aware_cooperative`.
80. `scenario.vehicle_classes.regular_taxonomy` is `car`, `bus`, `truck`, `motorcycle`, `bicycle`, `other`; special `emergency` remains separate and unknown regular labels fall back to `other`.
81. `legacy`, `mixed_urban`, and `freight_heavy` profiles are accepted; invalid profile is rejected through the existing traffic-rule validation path.
82. One run gives all modes the same deterministic class-rich base arrival fingerprint and class-count snapshot.
83. Per-intersection and network class metrics contain arrivals, transfer arrivals, served, wait distribution, and queue evidence.
84. Class-aware mode records selected class, weight, minimum waiting count, maximum extension, active flag, events, metrics, and `synthetic_vehicle_class_demand` provenance.
85. Direct class-method test shows vehicle-green extension remains inside phase/cycle/class cap.
86. Direct class-method test shows protected progression never shortens below the configured current-phase minimum.
87. Active pedestrian WALK/CLEAR demand blocks class-priority shortening.
88. Class weight `1.0` produces no class timing change.
89. Disabling class priority produces no class-priority events and class-aware network metrics match Pedestrian-aware Cooperative for the same run.
90. `comparisons.class_aware_cooperative_vs_pedestrian_aware_cooperative.selected_class` reports served/wait/queue deltas for the selected class.
91. Seven-mode CSV includes class-priority source/destination action/class/waiting/weighted-waiting/applied columns and preserves existing export conventions.
92. V029 emergency baseline/priority lifecycle and matched-event semantics remain unchanged.
93. V030 is described only as synthetic class-aware evidence; no live detector-accuracy, real transit/freight priority, hardware/public-road control, or safety claim is introduced.
94. Full inherited regression, structure check, backend live smoke, frontend typecheck/build, and repository `git diff --check` pass on the complete checkout.
95. Owner explicitly confirms V030 passed before `passed_baseline` changes.

## V031 persistent decision-evidence acceptance

96. `VERSION` reports `0_3_1`, previous `0_3_0`, passed baseline `0_2_4`, candidate status.
97. `docs/PATCH_0_3_1.md` and a V031 changelog section exist.
98. Retained V027 cooperation, V028 pedestrian-aware, V029 emergency-priority, V030 class-aware, and V031 decision-evidence focused regressions pass.
99. New network runs contain `decision_evidence.schema_version == 1`.
100. `record_count` equals the number of normalized records and `applied_count` is internally consistent.
101. Evidence IDs are unique/deterministic and individual records do not embed volatile random run IDs.
102. Trigger categories include applicable `scenario`, `cooperation`, `pedestrian`, `vehicle_class`, `emergency_priority`, and `emergency_lifecycle` records.
103. V031+ scenario evidence retains local observations when an active ranked scenario is exposed by the controller.
104. Each normalized record includes action/decision/applied, timing, grouped context, provenance, reason, explanation and `source_ref`.
105. `GET /api/traffic/network-experiments/{run_id}/evidence` returns the standard envelope and request ID.
106. `GET /api/traffic/network-experiments/{run_id}/evidence.csv` returns CSV with `X-Request-ID`.
107. Detailed mode-specific histories remain present; V031 does not replace/delete them.
108. An older stored V030 result without a V031 block can be projected through the evidence service without rewriting the historical JSON.
109. Same-seed/config repeated network runs preserve V030 repeatability semantics except normal top-level run metadata.
110. No V031 evidence code performs signal arbitration, changes phase order/timing, mutates live camera/controller state, or introduces physical/public-road signal authority.
111. Full inherited backend regression, live API smoke, frontend typecheck/build, structure check, and full-repository `git diff --check` pass on the owner checkout.
112. Owner explicitly confirms V031 passed before `passed_baseline` changes.
