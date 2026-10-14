# Patch 0_4_3 — UI visual consistency

Candidate `0_4_3`; previous candidate `0_4_2`; owner-accepted stable baseline `0_4_0`.

## Scope

- Shared theme tokens: blue/slate light and dark role palettes; no new design dependencies.
- Base controls: 40px height, stronger focus and field stroke; readable type hierarchy.
- App layout/components: consistent navigation, surface depth, panels, metrics, tables and responsive spacing.
- Active page CSS: removed hard-coded dark chrome from Settings, Dataset Review, Traffic Analytics, Live AI and Crosswalk Region Editor; kept semantic scene overlays separated.
- Simulation tabs and analytics toggles: visible selected state, keyboard focus and programmatic selected state.

## Research basis

Microsoft Fluent 2 color, spacing, button, tablist and card guidance; Material 3 surface roles; WCAG 2.2 contrast and focus targets. Exact references and parameters are in `docs/PC_STUDIO_DESIGN_SYSTEM.md`.

## Validation

Static palette/structure checks and sampled color contrast are checked before publishing. The actual Windows frontend build, live smoke and light/dark UI acceptance remain for owner testing. Use the existing one-line updater: `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests`.
