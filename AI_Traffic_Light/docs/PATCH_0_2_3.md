# Patch 0_2_3 — Configurable adaptive signal rules

## Release state

- Candidate: V023 / `0_2_3`
- Previous version: V022 / `0_2_2`
- Owner-confirmed passed baseline: V022 / `0_2_2`
- V023 remains a candidate until the owner completes acceptance checks and explicitly confirms it passed.

## Purpose

V023 replaces the simulator's single hard-coded signal-duration table with a persistent, user-configurable **simulation-only** policy. Users can edit normal timing and bounded adaptive rules while the simulator preserves a protected phase order and deterministic fallback behavior.

## Implemented

- Persistent signal policy configuration at runtime `config/signal_rules.json` (excluded from source patches).
- Normal-operation base/min/max timing for vehicle green, vehicle yellow, both all-red clearances, pedestrian WALK, and pedestrian CLEAR.
- Fixed / Adaptive / Test modes plus dry-run behavior.
- Profiles: Normal, Pedestrian Priority, Vehicle Priority, Accessibility.
- Structured rules for crossing occupancy/slow crossing, pedestrian queue/max wait, low vehicle demand, vehicle queue/max wait, mobility assistance, and fallen-person incident input.
- Rule priority/arbitration, persistence/hysteresis, cooldowns, demand memory, per-phase min/max clamps, maximum-cycle cap, and stale-observation fallback to normal timing.
- Protected phase sequencing; rules cannot jump directly between conflicting movement phases.
- Incident Test input holds the simulated signal at all-red until explicitly cleared; recovery restarts timing from the protected current phase without replaying elapsed time.
- Manual Test-mode inputs and non-mutating preview scenarios.
- Runtime reset separate from saved-rule reset.
- Persistent signal-decision audit history under `outputs/signal_rules/decision_history.jsonl` with explicit clear action.
- Traffic Logic UI tabs for Live Decision, Normal Timing, Adaptive Rules, Safety & Test, and Decision History.
- New signal-rule/status APIs with standard envelopes/request IDs.
- Simulation camera agents now consume the configurable controller phase/timing instead of the old fixed constant sequence.

## Deliberate limitations

- The current model is **not** claimed to detect wheelchairs/mobility assistance or a fallen person. Those inputs are Test-mode/manual unless a later compatible perception source is added.
- Slow-pedestrian/max-wait conditions use stable live demand/tracking context and short-term demand memory; this is prototype logic, not certified safety instrumentation.
- Rule construction is structured and bounded; V023 intentionally does not implement an arbitrary Boolean scripting language.
- Configuration import/export and automated A/B policy benchmarking remain future work.
- No physical/public-road traffic signal control is added.

## Runtime data

Never package or overwrite local:

- `config/signal_rules.json`
- `outputs/signal_rules/`
- existing `datasets/`, `outputs/traffic_history/`, `outputs/traffic_flow/`, training outputs, models, labels, zones, or settings.

## New/changed API surface

- `GET /api/traffic/signal-rules`
- `PUT /api/traffic/signal-rules`
- `POST /api/traffic/signal-rules/reset`
- `POST /api/traffic/signal-rules/runtime/reset`
- `POST /api/traffic/signal-rules/test-inputs`
- `POST /api/traffic/signal-rules/incident/clear`
- `POST /api/traffic/signal-rules/preview`
- `GET /api/traffic/signal-status`
- `GET /api/traffic/signal-rules/history`
- `DELETE /api/traffic/signal-rules/history`

See `docs/API_CONTRACTS.md` and `docs/TEST_READY_CHECKLIST.md`.


## Same-candidate regression repair

- Fixed the stateful signal controller when the private simulation clock is intentionally moved backwards by inherited deterministic camera-simulation tests or an explicit simulation reset.
- The controller now rebuilds transient phase state from cycle start on clock rewind, preserving the configured protected phase sequence instead of retaining a phase whose start time is in the future.
- Added a focused rewind regression assertion to `scripts/test_signal_rules_service.py`.
- Version remains `0_2_3`; this repair does not promote the owner-confirmed `0_2_2` passed baseline.

## Same-candidate standalone test import repair

- Added the PC Studio backend directory to `scripts/test_signal_rules_service.py` before importing `app`, matching the established standalone test-script pattern.
- Fixes `ModuleNotFoundError: No module named 'app'` when the test is run from the `AI_Traffic_Light` project root with the backend virtual environment active.
- Application/controller behavior is unchanged; version remains `0_2_3` and passed baseline remains `0_2_2`.

## Same-candidate Traffic Logic assertion repair

- Updated `scripts/test_zone_traffic_services.py` to assert the V023 explanation text `Detection recommendation:` instead of the pre-V023 wording `Detection-based recommendation`.
- The existing recommendation metadata assertions remain unchanged, so the test still verifies that the active simulation signal and detection-driven recommendation are both retained.
- No application/runtime behavior changed; version remains `0_2_3` and passed baseline remains `0_2_2`.
