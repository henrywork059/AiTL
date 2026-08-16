# V023 acceptance checklist

V023 / `0_2_3` is the current candidate. V022 / `0_2_2` is the owner-confirmed passed baseline. Automated tests do not promote V023.

## Release / packaging

1. `VERSION` reports `version: 0_2_3`, `previous_version: 0_2_2`, `passed_baseline: 0_2_2`, and candidate status.
2. `check_structure.py`, Python compilation, backend regression tests, frontend typecheck/build, live smoke, and `git diff --check` pass locally.
3. Patch ZIP is changed-files-only, all members start `AI_Traffic_Light/`, validator passes, and no runtime/generated/model files are present.

## Normal timing and persistence

4. Traffic Logic shows Live Decision / Normal Timing / Adaptive Rules / Safety & Test / Decision History tabs.
5. Six protected phase entries expose min/base/max timing.
6. Valid timing edits save and persist after backend restart.
7. Invalid protected minimum/order/cycle values are rejected without corrupting the prior configuration.
8. Saving/resetting rules during an active simulation does not replay clock time or skip rapidly through phases.
9. Fixed mode follows configured normal timing only.

## Adaptive arbitration

10. Heavy vehicle demand can make one bounded vehicle-green extension after persistence.
11. Heavy/long-wait pedestrian demand can make a bounded vehicle-green reduction.
12. Crossing/slow-crossing conditions can retain/extend pedestrian clearance as configured.
13. No adaptive reduction goes below phase minimum or already-served time.
14. Total extension remains bounded by phase maximum and maximum-cycle policy.
15. Cooldown prevents repeated per-poll accumulation.
16. Persistence/hysteresis prevents single-frame spikes; demand memory bridges short dropouts.
17. Stale/missing adaptive observations produce explained fallback to normal configured timing.
18. Rule arbitration shows active/suppressed/inactive/unavailable states and reasons.
19. Pending demand is visible and never creates an invalid phase jump.

## Protected sequence / incident behavior

20. Phase order remains vehicle green → yellow → all-red → pedestrian WALK → pedestrian CLEAR → all-red.
21. Yellow/all-red protected minimums cannot be configured below enforced lower bounds.
22. Test-mode fallen-person incident enters simulated all-red hold.
23. Incident does not claim live fall detection unless a compatible perception source exists.
24. Clear Incident exits hold safely and restarts timing from the protected current phase.
25. Reset Adaptive State clears transient state without deleting saved configuration.

## Accessibility / test / preview

26. Manual mobility assistance exists only as an explicit Test-mode source in V023.
27. UI/docs do not claim current YOLO detects wheelchairs, mobility assistance, or falls.
28. Manual test counts can exercise pedestrian/vehicle rules.
29. Preview evaluates representative scenarios without mutating active runtime state.
30. Dry-run shows rule evaluation without applying adaptive timing changes.
31. Profiles can be selected and saved.

## History / regression / safety

32. Signal decision history records relevant phase/rule/config/reset/incident events and persists under `outputs/signal_rules/`.
33. Clear Signal Decision History deletes only that history.
34. Existing occupancy history and V022 flow/tracking remain separate and functional.
35. Simulation density/pause, lane/stop-line behavior, pedestrian crosswalk behavior, camera receiver, zones, capture/delete/labels, training, inference/model registry, settings, and logs show no regression.
36. Runtime `config/signal_rules.json` and `outputs/signal_rules/` are absent from source patch ZIP.
37. Nothing in V023 controls or connects to physical/public-road traffic-signal infrastructure.
38. Owner completes manual/UI checks and explicitly confirms V023 passed before `passed_baseline` changes.
