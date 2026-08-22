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
39. Emergency priority remains inactive.
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
54. Emergency priority remains inactive and no public-road control claim is introduced.
55. Full inherited regression, structure check, frontend typecheck/build and live smoke pass locally before owner acceptance.
