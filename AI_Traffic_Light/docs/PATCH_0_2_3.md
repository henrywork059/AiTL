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

## Same-candidate PC Studio design-system patch

- Centralized shared visual decisions under `apps/pc-studio/frontend/src/styles/`: `tokens.css`, `base.css`, `layout.css`, and `components.css`, with `src/styles.css` retained as the stable entrypoint.
- Added `docs/PC_STUDIO_DESIGN_SYSTEM.md` as the authoritative visual-style contract and linked it from the GUI layout/frontend README.
- Restyled PC Studio as a restrained dark operations/workbench interface: solid graphite surfaces, smaller 4–8px radii, low elevation, neutral navigation, and desaturated semantic status colors.
- Removed the decorative page gradient and generic purple/neon AI-like accent treatment from shared UI and Traffic Logic styling.
- Kept page-specific `signalRules.css` for Traffic Logic structure while moving its palette/geometry decisions onto shared tokens.
- Added a visible keyboard focus treatment and standardized field/button styling without adding any frontend dependency or webfont.
- Research direction was informed by IBM Carbon, GitHub Primer, Atlassian Design System, and GOV.UK guidance on role-based tokens, layering, compact geometry, and systematic spacing; AiTL remains its own implementation.
- No API, backend, signal-rule, inference, dataset, training, tracking, or persisted runtime-data behavior changed.
- Version remains `0_2_3`; owner-confirmed passed baseline remains `0_2_2`.

### Visual acceptance checks

- Every main page uses the same graphite canvas/shell/panel hierarchy with no full-page gradient or translucent glass panels.
- Sidebar active state is neutral with a narrow accent edge rather than a saturated blue tile.
- Standard panels and controls use compact radii; status pills remain the only general pill-shaped element.
- Traffic Logic tabs/rule cards consume the same tokens as the rest of PC Studio.
- Success/warning/error states remain distinguishable and include textual labels/reasons.
- Keyboard tabbing shows a visible focus outline on buttons/inputs/selects/textareas/links.
- Live AI/Zone overlay colors remain distinguishable after the palette change.
- Frontend `npm run typecheck` and `npm run build` pass.
## Reference-informed design-system refinement

- Refined the same-candidate PC Studio visual-system patch using the owner-supplied Apple HIG, UX Pilot color-theory, Figma color-theory, and Material Design 2 color-system references.
- Added automatic `prefers-color-scheme` light/dark appearance rather than forcing a dark-only app identity.
- Reworked shared tokens around explicit background/surface/raised/field, on-surface text, interaction, and semantic-state roles.
- Kept the palette narrow: neutral layers dominate, one muted steel-blue family communicates interaction, and green/amber/red remain semantic/simulated-signal colors rather than decorative technology accents.
- Strengthened hierarchy with base/elevated surface separation and a page-header divider while retaining compact desktop spacing/radii.
- Added `prefers-contrast: more`, `prefers-reduced-motion: reduce`, `forced-colors`, focus-visible, and system selection treatments.
- Preserved dedicated high-contrast camera/zone/detection overlay colors independently of the application appearance.
- No backend, API, signal-rule, training, dataset, inference, tracking, or traffic-analytics behavior changed. Version remains `0_2_3`; passed baseline remains `0_2_2`.

