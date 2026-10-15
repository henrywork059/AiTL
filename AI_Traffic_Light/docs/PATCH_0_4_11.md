# Patch 0_4_11 — Junction node layout and fluid text

**Candidate:** `0_4_11` · **Previous candidate:** `0_4_10` · **Accepted baseline:** `0_4_0`

## Scope

Junction Network card-only layout change:

- Move junction name, ID and active state to the existing draggable title bar.
- Introduce a three-column, three-row CSS grid below the title bar for centered vehicle/pedestrian loads, camera count, phase and warnings/events.
- Put clickable labels 1–4 at the four sides of the central content: north, east, south and west. Keep current numeric mapping, tooltips, aria-pressed, crosswalk assignments and edge connection behavior.
- Use a fluid card width, container-relative `clamp(...cqi...)` font sizes, wrapping and content-driven height. Avoid ellipsis/nowrap in junction card text.
- Align historical layout tests, and add an isolated V0411 structure/layout regression.

No backend, data schema, signals, node drag computation, camera, API or theme-palette changes.

## Validation

Source-level checks are available. Frontend `npm run typecheck`, production build, live smoke and actual desktop/narrow-screen visual verification remain pending Windows owner validation.

From repository root:
```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
