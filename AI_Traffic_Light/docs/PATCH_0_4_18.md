# Patch 0_4_18 — Selectable cameras, simplified simulator and region UI

Candidate `0_4_18` · Previous candidate `0_4_17` · Owner-accepted stable baseline `0_4_14`.

## Scope and boundaries

- Camera Settings → Saved cameras now displays each camera as an interactive button inside its existing list item. Buttons reuse the prior async `chooseSavedCamera` service and existing stream/state refresh. No new API or camera-selection state exists.
- Simulation **pixels only**: draw the same roads/crosswalk, only car and pedestrian actors; remove text overlays, STOP labels, bus visual actors and drawn signal/pedestrian lamp panels. Signal-phase logic and safety transitions remain unchanged and can still be queried through the existing status API.
- Crosswalk Region Editor camera-side selection changes from a dropdown to accessible Side A/B toggle buttons. Preview camera assignment and polygon coordinates are not mutated by switching sides.
- Region polygons use SVG `fill="none"` and `fillOpacity={0}`, preserving the previously requested transparent interiors and thicker dashed selected outline. Vertex handles remain draggable.
- Global status pills are inline flex with centered content, correcting the offset `Simulation active` text.
- Full original source for six affected files is stored in `docs/backups/V0417_PRE_V0418_CODE.md` with explicit failure-prevention notes, anchored to the immutable V0417 commit. Do **not** import archived source into runtime.

## Focused checks

`test_v0418_camera_region_ui.py` checks camera click wiring, toggle accessibility, region transparency, status alignment, renderer source contracts and backup integrity. The older `test_simulation_frame_layout.py` now tests removal of metadata/signal visuals rather than their presence. Run the full Windows updater for Python tests, TypeScript/build and backend live smoke; only user-confirmed PASS accepts V0418.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
