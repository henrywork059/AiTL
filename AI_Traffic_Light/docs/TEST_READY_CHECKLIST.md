# V054 Candidate Checklist

```text
version: 0_5_4
previous_version: 0_5_3
passed_baseline: 0_5_0
status: Camera-scoped counting candidate
```

- [ ] Different regions and IDs per camera side, Save regions persists both.
- [ ] Count detected classes only for active camera; no signal policy changes.
- [ ] Windows frontend build, smoke and user acceptance.

## V053 Release Consistency Candidate

```text
version: 0_5_3
previous_version: 0_5_2
passed_baseline: 0_5_0
status: V052 release metadata repair candidate
```

- [ ] Simulator controls and Experiments initially hidden; physical ESP options remain usable.
- [ ] Brand toggle by click/Enter/Space reveals/hides simulator tools across Camera Settings, Crosswalks, Region Editor and Junction Network.
- [ ] Saved source state, assignments and signal behavior unchanged; run Windows frontend tests and app smoke.

## V053 acceptance

- Verify update runner structure/version validation, frontend typecheck/build, backend smoke and Region Editor Save regions persistence.
- V052 Save regions implementation remains unchanged. Owner PASS pending.

## V0501 acceptance


```text
version: 0_5_0
previous_version: 0_4_24
passed_baseline: 0_5_0
status: Owner-accepted stable release
```

- [x] Owner confirmed PASS for `0_4_24` and explicitly requested the next stable version.
- [x] No application code, API, camera, hardware, data or signal logic changed for the V050 promotion.
- [ ] Optional local confirmation: app displays `0_5_0 Stable`.
- [ ] Optional local revalidation: Windows updater/test runner and existing Crosswalk/Region Editor acceptance paths.

## Historical V0424 and earlier checks (archival)


```text
version: 0_4_24
previous_version: 0_4_23
passed_baseline: 0_4_14
status: Crosswalk camera-side layout candidate
```

- [ ] Side A appears left and Side B right, each with one camera selector and its status above the schematic.
- [ ] The duplicate camera status section and the bottom Side B selector are removed.
- [ ] At narrow widths the columns stack without clipping.
- [ ] Camera assignments, status updates, save/reload, missing-source warnings and simulation remain functional.
- [ ] Focused Crosswalk regression, frontend typecheck/build, backend smoke and actual Windows browser layout are verified.

## Historical V0423 and earlier checks (archival)


```text
version: 0_4_23
previous_version: 0_4_22
passed_baseline: 0_4_14
status: Translucent region overlay candidate
```

- [ ] Crosswalk Region Editor unselected polygons show mint RGBA 0.10 fill over a visible camera frame.
- [ ] Selected polygon shows pale cream RGBA 0.22 fill, fully opaque 6px pale-yellow dashed stroke and draggable numbered vertices.
- [ ] Side A/B previews, geometry save/reload and both simulation camera pairs work normally.
- [ ] Hidden legacy editor uses the equivalent 0.10/0.22 translucent fills; Live AI/simulation overlays remain clear and dataset boxes unchanged.
- [ ] Focused Python regressions, frontend typecheck/build, backend smoke, startup and browser appearance are verified.

## Historical V0422 and earlier checks (archival; superseded appearance)

```text
version: 0_4_22
previous_version: 0_4_21
passed_baseline: 0_4_14
status: Responsive text layout and clear selected-region outline candidate
```

- [ ] Shared headings, buttons, status pills, cards and panel headers resize or wrap without text clipping.
- [ ] Junction camera IDs/link labels, Signal Control scenario descriptions and Simulation Experiment summaries show complete text.
- [ ] Short-height desktop windows can scroll Simulation Experiment results; data tables remain horizontally scrollable where necessary.
- [ ] Both selected and unselected region interiors remain fully clear; selected outline is thicker and brighter.
- [ ] Selected Python regressions, frontend typecheck/build, backend startup and live smoke pass.
- [ ] Camera Settings can add Pair 1 and then a second pair (C/D); all four saved IDs persist after restart.
- [ ] Saved camera selection and preview stream work for A/B/C/D; corresponding views are mirrored and share one signal-clock simulation.
- [ ] Deleting one simulation pair preserves the other pair and unrelated ESP profiles.
- [ ] Crosswalk camera-side dropdowns can select Pair 2 cameras, and saving/reloading keeps assignments.
- [ ] Python regressions, frontend typecheck/build, backend smoke and startup pass.
- [ ] Unselected Crosswalk Region polygons are fully transparent.
- [ ] Selected polygon has no fill, visible camera, brighter yellow dashed border and editable vertices.
- [ ] Legacy selected regions match; Live AI and simulation overlays remain fully transparent.
- [ ] Regression tests, frontend typecheck/build, backend smoke and startup pass.
- [ ] V0418 regression examines all matching camera-status-entry CSS declarations (cursor + background).
- [ ] All selected offline regressions, frontend typecheck/build, backend live smoke and startup pass on Windows.
- [ ] Saved cameras click selects the camera and shows the correct stream; keyboard and busy states work.
- [ ] Simulation frames contain only cars/people on the road/crossing, without labels or signal heads; signal-state API and behavior are intact.
- [ ] Crosswalk region Camera side uses selectable Side A/B toggle buttons.
- [ ] Region polygons remain completely unfilled, selected outlines/handles remain visible.
- [ ] Simulation active pill text is centered in its rounded border.
- [ ] Pre-patch source and regression reminder archive exists.
- [ ] TypeScript/build, Python regressions, startup and backend live smoke pass.
- [ ] Crosswalk region polygons are completely transparent in both normal and selected states, with outlines and draggable vertices preserved.
- [ ] Live AI and simulation region outlines remain visible without hiding camera frames.
- [ ] Dataset Review bounding boxes are unchanged; region geometry and saves work normally.
- [ ] Frontend typecheck/build and backend smoke pass.
- [ ] Traffic sidebar has no empty Zones page; Junctions and Crosswalks remain.
- [ ] Crosswalks → Edit regions still creates/edits/saves the same region geometry.
- [ ] Live AI, Signal Control, Analytics and feature descriptions show Region/Regions wording.
- [ ] Existing `/api/zones`, `zone_id` and saved configs remain fully compatible.
- [ ] Python regressions, TypeScript build, backend live smoke and app startup pass.
- [ ] Main dark canvas uses `#444557` without changing the sidebar, panels, mint accent or light mode.
- [ ] Palette/design regressions, frontend build, startup and live smoke pass on Windows.
- [ ] Old V0409 palette regression no longer requires `color-nav-heading-surface`.
- [ ] V0413 dedicated navigation regression still verifies the current sidebar.
- [ ] Python regressions, frontend typecheck/build, live backend smoke and app startup pass.
- [ ] Sidebar group headings use muted text and hairline divider instead of mint-bordered boxes.
- [ ] Selected navigation row uses neutral slate, no mint bar or dot, with clear text contrast.
- [ ] Sidebar hover remains subtle and keyboard focus is visibly outlined; other mint control states remain.
- [ ] Light/dark appearance and navigation work; frontend typecheck/build and smoke pass.
- [ ] V0411 layout regression checks the last alert CSS declaration and does not stop on its earlier grouped selector.
- [ ] Windows typecheck, frontend build, live smoke and app startup proceed.
- [ ] Junction cards display full-width draggable title bar with name and ID.
- [ ] Junction load, camera count, phase and alert statuses remain centered and readable without clipping.
- [ ] Numbered edge controls are placed north/east/south/west of the information area, not the whole card.
- [ ] Long names/IDs/statuses wrap and font sizes scale with card width at desktop/mobile sizes.
- [ ] Edge selection, node dragging, crosswalk linking and frontend typecheck/build work.
- [ ] Camera Settings ESP-only form has no unreachable `simulation` comparisons (TS2367).
- [ ] `npm run typecheck` and `npm run build` pass locally.
- [ ] ESP Save/Connect enable/disable states and simulation-pair creation work normally.
- [ ] Dark canvas `#4D4E61` and opaque sidebar, input, panel, selected, and semantic layers are legible.
- [ ] Sidebar brand and each navigation group title are visually separated from page links.
- [ ] Junction edge labels 1–4 are inside the card and leave all card data and drag handle accessible.
- [ ] Light mode and selected/toggled mint/teal styling remain usable; frontend build passes.
- [ ] Mocked Windows PowerShell worker/parent identity regression passes.
- [ ] System-Python Uvicorn child on port 8000 restarts through verified AiTL parent.
- [ ] Application startup and backend health/live smoke pass; unrelated processes remain untouched.
- [ ] Windows runner safely restarts project Uvicorn reload parent/worker on port 8000, without closing unrelated processes.
- [ ] Other Python services on port 8000 remain protected.
- [ ] Backend health, frontend launch and smoke pass.
- [ ] Junction Network regression asserts current mode text and primary-camera selector, not removed copy.
- [ ] Windows update/test/run continues past the prior Junction Network failure.
- [ ] Dark mode displays `#57FFED` accent; light mode uses accessible dark teal.
- [ ] Selected navigation, tabs, mode buttons, Crosswalks and Dataset rows show dots/bars/rings as applicable.
- [ ] Live AI checked filters and Junction edge selection have visible active styling.
- [ ] Keyboard focus, button hover, app startup and existing camera/junction behavior remain correct.
- [ ] Updated structure validator accepts the new semantic dark base token and rejects an invalid token.
- [ ] V0404 changed-tests startup proceeds beyond the previous structure failure.
- [ ] Shared semantic palette passes contrast validation; light/dark page styles share tokens.
- [ ] Buttons, input fields, panels, navigation selection and analytics/simulation tabs are usable.
- [ ] Simulation tabs support keyboard navigation; chart labels remain readable.
- [ ] Windows build and live smoke pass; prior functionality unchanged.
- [ ] Crosswalk static regression passes with mirrored-pair assertions.
- [ ] Both simulation profiles are saved and are vertically mirrored views of the same scene.
- [ ] Crosswalk labels 1–4, pair assignment, preview, region editor and save/restart are valid.
- [ ] Junction drag has no initial jump; edge controls do not overlay text.
- [ ] Legacy pages are hidden but remain reachable in code; new Zones page is blank.
- [ ] Dashboard, Camera Settings and Crosswalks have no test-ready labels; page titles are concise.
- [ ] Windows changed-tests startup, typecheck/build and live smoke pass; existing ESP and configuration remain intact.

## Prior acceptance history

- [ ] Camera Settings regression asserts both selected simulation and physical ESP preview isolation and passes.
- [ ] Windows changed-tests startup completes all selected regressions, frontend checks, backend health and live smoke.
- [ ] New Camera supports selecting and saving one simulation camera without IP; its preview and Crosswalk assignment work after restart.
- [ ] Junctions show 1–4 edge labels with no N/E/S/W visible; topology links persist selected endpoint numbers.
- [ ] Existing crosswalk-to-edge mappings and physical ESP stream controls remain intact.
- [ ] Camera Settings and Crosswalks page regressions pass without relying on adjacent entries in `CAMERA_POLL_PAGES`.
- [ ] Windows update/test/run completes, frontend opens and backend health/live smoke pass.
- [ ] V0324 junction-edge acceptance checks below still pass.


- [ ] All junction cards show clickable N/E/S/W edge labels, linked/selected styling and tooltips.
- [ ] Selecting an edge opens its crossing assignment in Junction Network inspector.
- [ ] The dropdown lists saved crosswalks, shows missing references and supports No crosswalk.
- [ ] One crossing cannot occupy more than one edge; backend rejects duplicate or malformed IDs.
- [ ] Older network JSON without `crosswalk_edges` loads as four empty edges; save/restart preserves mappings.
- [ ] Existing junction camera, simulation, drag, topology and traffic state behaviors remain unchanged.
- [ ] `python scripts/test_intersection_network.py` passes.
- [ ] `python scripts/test_junction_network_frontend_structure.py` passes.
- [ ] `python scripts/check_structure.py`, frontend typecheck/build and full Windows runner pass.
- [ ] Owner confirms PASS, otherwise `0_4_0` remains accepted baseline.
