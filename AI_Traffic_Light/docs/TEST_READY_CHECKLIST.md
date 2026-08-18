# V024 acceptance checklist

V024 / `0_2_4` is the current candidate. V023 / `0_2_3` is the previous candidate; V022 / `0_2_2` remains the owner-confirmed passed baseline. Automated tests do not promote V024.

## Release / packaging

- The Windows helper `scripts/update_test_run.ps1` must pass `scripts/test_update_test_run_script.py`, refuse tracked local edits/non-main updates, reload itself after pull, and run the live smoke only after backend health is ready.

1. `VERSION` reports `version: 0_2_4`, `previous_version: 0_2_3`, `passed_baseline: 0_2_2`, and candidate status.
2. `check_structure.py`, Python compilation, backend regression tests, frontend typecheck/build, live smoke, and `git diff --check` pass locally.
3. Patch ZIP is changed-files-only, all members start `AI_Traffic_Light/`, validator passes, and no runtime/generated/model files are present.


## V024 persistence / polling hardening

4. `core/json_store.py` uses unique same-directory temporary files, flush/fsync, and atomic replace.
5. A serialization/write failure does not replace the previous valid JSON target and cleans the unique temporary file.
6. Runtime settings, zones, and model-registry metadata use the shared atomic writer while preserving existing validation/errors.
7. Zone reads/saves are serialized by the zone service lock.
8. Model-registry discovery/default/delete/metadata transitions are synchronized by a re-entrant lock.
9. App-level camera-status and Live AI traffic/zone polling use `useSerialPolling`, not raw `setInterval`.
10. A slow migrated poll cannot overlap another request from the same polling loop, and leaving the relevant page cancels future schedules.


## V024 presentation / interface copy

- Neutral application surfaces remain dominant in both light and dark appearance.
- Primary blue is used for active navigation, links/focus, and dominant workflow actions; it is not used as a decorative panel fill.
- Secondary teal is sparse and used for selected secondary state/progress.
- Generic status/count/context pills are neutral; success/warning/error colors are applied only when those meanings are true.
- Dark mode preserves the Material-derived `#121212` base and neutral elevation ramp.
- Primary/secondary colored controls use explicit readable on-color roles.
- Working page descriptions and panel labels describe current tasks/state rather than old V021/V022/V023 implementation history.
- `Confirm layout first` and stale Live AI `0_2_0` presentation text are absent.
- Destructive actions use explicit destructive styling/copy and confirmations explain what is removed.
- Copy remains precise about occupancy vs. flow, active vs. default model, and simulation-only signal behavior.

## Inherited V023 signal behavior

11. Traffic Logic shows Live Decision / Normal Timing / Adaptive Rules / Safety & Test / Decision History tabs.
12. Six protected phase entries expose min/base/max timing.
13. Valid timing edits save and persist after backend restart.
14. Invalid protected minimum/order/cycle values are rejected without corrupting the prior configuration.
15. Saving/resetting rules during an active simulation does not replay clock time or skip rapidly through phases.
16. Fixed mode follows configured normal timing only.

## Adaptive arbitration

17. Heavy vehicle demand can make one bounded vehicle-green extension after persistence.
18. Heavy/long-wait pedestrian demand can make a bounded vehicle-green reduction.
19. Crossing/slow-crossing conditions can retain/extend pedestrian clearance as configured.
20. No adaptive reduction goes below phase minimum or already-served time.
21. Total extension remains bounded by phase maximum and maximum-cycle policy.
22. Cooldown prevents repeated per-poll accumulation.
23. Persistence/hysteresis prevents single-frame spikes; demand memory bridges short dropouts.
24. Stale/missing adaptive observations produce explained fallback to normal configured timing.
25. Rule arbitration shows active/suppressed/inactive/unavailable states and reasons.
26. Pending demand is visible and never creates an invalid phase jump.

## Protected sequence / incident behavior

27. Phase order remains vehicle green → yellow → all-red → pedestrian WALK → pedestrian CLEAR → all-red.
28. Yellow/all-red protected minimums cannot be configured below enforced lower bounds.
29. Test-mode fallen-person incident enters simulated all-red hold.
30. Incident does not claim live fall detection unless a compatible perception source exists.
31. Clear Incident exits hold safely and restarts timing from the protected current phase.
32. Reset Adaptive State clears transient state without deleting saved configuration.

## Accessibility / test / preview

33. Manual mobility assistance exists only as an explicit Test-mode source in V023+.
34. UI/docs do not claim current YOLO detects wheelchairs, mobility assistance, or falls.
35. Manual test counts can exercise pedestrian/vehicle rules.
36. Preview evaluates representative scenarios without mutating active runtime state.
37. Dry-run shows rule evaluation without applying adaptive timing changes.
38. Profiles can be selected and saved.

## History / regression / safety

39. Signal decision history records relevant phase/rule/config/reset/incident events and persists under `outputs/signal_rules/`.
40. Clear Signal Decision History deletes only that history.
41. Existing occupancy history and V022 flow/tracking remain separate and functional.
42. Simulation density/pause, lane/stop-line behavior, pedestrian crosswalk behavior, camera receiver, zones, capture/delete/labels, training, inference/model registry, settings, and logs show no regression.
43. Runtime `config/signal_rules.json` and `outputs/signal_rules/` are absent from source patch ZIP.
44. Nothing in V024 controls or connects to physical/public-road traffic-signal infrastructure.
45. Owner completes manual/UI checks and explicitly confirms V024 passed before `passed_baseline` changes.
