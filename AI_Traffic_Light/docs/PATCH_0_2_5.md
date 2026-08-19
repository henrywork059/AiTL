# Patch 0_2_5 — Ranked Signal Scenarios + Simulation Lab

## Release state

- Candidate: V025 / `0_2_5`.
- Previous version: V024 / `0_2_4`.
- Owner-confirmed passed baseline: V024 / `0_2_4`.
- V025 remains an unaccepted candidate until the owner explicitly promotes it.

## Purpose

V025 now has two connected prototype goals:

1. replace the mostly predefined adaptive-rule UI with user-defined, ranked traffic scenarios; and
2. measure Fixed versus Adaptive behavior in the isolated Simulation Lab using richer telemetry.

Nothing in this patch connects to physical/public-road traffic infrastructure.

## Ranked signal scenarios

Traffic Logic stores scenarios inside each signal profile. A scenario contains:

- stable `id` and editable `label`;
- enabled/disabled state;
- numeric `rank` where **1 is highest**;
- `match: all | any`;
- 1–8 trigger conditions;
- persistence and cooldown seconds;
- one bounded signal action;
- allowed protected target phases;
- optional requested service (`pedestrian | vehicle`).

### Condition sources

A condition can use a controller metric such as:

- pedestrians waiting/crossing;
- vehicles waiting;
- pedestrian or vehicle wait duration;
- crossing dwell duration;
- explicit Test-mode mobility/incident flags.

Or it can use a zone/class observation:

```text
class <operator> threshold in zone
```

Examples:

```text
car > 5 in queue_east
person >= 3 in waiting_west
* > 8 in counting_region_1
```

`*` means all detected classes in that polygon zone. Missing/deleted zones are reported as unavailable rather than silently treated as zero.

### Arbitration

Multiple scenarios can be triggered at once. The controller sorts by rank and executes only the highest-ranked **eligible** scenario in one evaluation.

A higher-ranked scenario does not block the next scenario when it is:

- disabled;
- based on stale/unavailable observations;
- missing a referenced zone;
- still inside its persistence window;
- not allowed during the current protected phase; or
- inside cooldown.

The live UI exposes winner / suppressed / inactive / unavailable states plus observed condition values and reasons.

### Actions and protected timing

Supported actions remain bounded simulation actions:

- extend current phase;
- reduce current phase;
- hold current phase / keep clearance;
- request the next protected phase sooner;
- Test-mode incident all-red hold.

A scenario never directly jumps from one conflicting movement to another. The protected order remains:

```text
vehicle green → vehicle yellow → all-red → pedestrian WALK → pedestrian CLEAR → all-red
```

Protected minimums, per-phase maximums, maximum-cycle limits, already-served time, persistence, cooldown, stale fallback and incident recovery remain enforced.

### Compatibility

Older saved V023/V024 signal configurations contain `rules` but no `scenarios`. V025 validates those files and migrates the legacy rules into editable scenario definitions while preserving the old ids, ordering intent, thresholds, phase targets and response amounts. The legacy `rules` data remains in the config for compatibility, but V025 adaptive arbitration uses `scenarios`.

## Traffic observations

`GET /api/traffic/state` now also returns:

```json
"zone_class_counts": {
  "queue_east": {"car": 4, "bus": 1},
  "waiting_west": {"person": 3}
}
```

The counts are per-frame detector observations. Arbitrary detected class names are preserved for scenario conditions even when they are not part of the existing pedestrian/vehicle occupancy groups.

This does **not** change analytics semantics:

- occupancy is still sampled presence;
- flow is still track-derived line/region events;
- zone/class counts are scenario observations, not throughput.

## Traffic Logic presentation

Traffic Logic remains one page with grouped tabs:

- **Live Decision** — current phase, winner, full ranked arbitration and live zone/class counts;
- **Signal Timing** — protected min/base/max timings and controller guards;
- **Scenario Rules** — scenario list plus selected-scenario editor;
- **Test & Safety** — manual Test-mode inputs, preview/reset/incident controls;
- **History** — phase/config/incident/scenario execution history.

Scenario editing uses select menus, rank/threshold inputs, ALL/ANY selection, Add/Remove Condition buttons, action selection, requested-service selection, protected-phase checkboxes, duplicate/delete controls, internal panels and bounded scrolling rather than expanding every scenario inline.

## Simulation Lab integration

The existing V025 Fixed-vs-Adaptive Simulation Lab remains isolated from the live camera/controller runtime. V025 now snapshots the configured zones at experiment start and computes synthetic per-zone/per-class observations from the numeric agents. This lets zone-based scenarios participate in the isolated Adaptive benchmark.

The experiment still records:

- vehicle/pedestrian wait count, average, median, p95, max and total;
- queue average, p95, peak, queue-seconds and active share;
- simultaneous queue time;
- vehicle/pedestrian/combined throughput;
- vehicle passages per green minute;
- phase time/share, transitions and cycles;
- clearance time/share;
- scenario application counts and timing extension/reduction totals;
- conflict-overlap diagnostic;
- paginated raw timeline samples.

Results persist under `outputs/simulation_experiments/` and can be reopened, exported as aligned Fixed/Adaptive CSV, or explicitly deleted.

## Stable API/error behavior

No new stable error range is required for the scenario rework. Invalid scenario ids, ranks, conditions, operators, phase targets and actions use the existing `ATL-TRAFFIC-002` traffic-rule validation error.

V025 experiment storage continues to use `ATL-TRAFFIC-010..012`.

## Limitations

- Scenario class counts depend on the active detector/class labels for live camera operation.
- Zone/class scenarios referencing a deleted zone become unavailable until edited.
- The current detector is not claimed to identify mobility assistance or falls; those remain explicit Test-mode flags.
- Simulation Lab is a local deterministic prototype benchmark, not a calibrated traffic microsimulator.
- Conflict-overlap is a simulator diagnostic only, not a safety certification metric.
- Results do not establish real-world/public-road performance.

## Primary acceptance checks

1. Open Traffic → **Traffic Logic** and confirm the tabs are Live Decision / Signal Timing / Scenario Rules / Test & Safety / History.
2. Create a zone/class scenario such as `car > 2` in a vehicle queue zone, rank `1`, action Extend current phase by 4s, target Vehicle green; save it.
3. Create a second scenario that is also true but has rank `2`; confirm Live Decision shows rank 1 as the winner and rank 2 as suppressed by arbitration.
4. Change rank 2 to rank 1 and the former rank 1 to rank 2; save and confirm the winner changes deterministically.
5. Reference a nonexistent/deleted zone in the higher-ranked scenario; confirm it becomes unavailable and does not block the next eligible scenario.
6. Configure a scenario with two conditions and ALL matching; confirm it triggers only when both values match. Switch to ANY and confirm either condition is sufficient.
7. Verify observed zone/class values appear beside scenario condition status.
8. Verify persistence prevents a one-frame trigger and cooldown prevents repeated phase adjustment.
9. Verify a scenario whose action is not allowed in the current phase does not execute and the next eligible scenario may win.
10. Verify phase minimums, maximums and protected transition sequence remain enforced.
11. Verify Fixed mode performs no adaptive scenario action.
12. Verify Test-mode incident/accessibility inputs remain clearly manual/Test-only.
13. Run Simulation Lab with the same profile/zones and confirm a zone-based scenario appears in Adaptive scenario-application telemetry when its synthetic condition occurs.
14. Confirm running Simulation Lab does not reset the live camera simulation/controller.
15. Re-run full inherited V024 persistence/polling, V022 tracking/flow, V021 occupancy, dataset/training/inference/model/settings/log checks.
16. Confirm no feature controls physical/public-road traffic infrastructure.

## Safety

All signal scenarios, comparisons and phase outputs remain local prototype/simulation information. Physical/public-road traffic control remains disabled and outside project scope.
