# V0515 — Interactive 3D Simulation Lab (candidate)

- [ ] Feature branch checked out; `main` unchanged.
- [ ] Project version/structure checks and frontend TypeScript/Vite build pass.
- [ ] Simulation Lab's 3D Replay tab renders with a saved/new experiment.
- [ ] Fixed/Adaptive switching resets playback and reflects the selected mode's samples.
- [ ] Play/Pause, scrub, orbit, pitch, zoom and Reset view work without a backend mutation.
- [ ] Vehicle and pedestrian queue counts and signal labels match raw sample values; object positions are labeled illustrative.
- [ ] Empty and narrow-screen layouts remain usable, legacy charts/tabs and simulation controls work.
- [ ] Owner confirms PASS. Accepted baseline remains `0_5_0`.

---

# V0514 Release Consistency Repair Candidate

```text
version: 0_5_14
previous_version: 0_5_13
passed_baseline: 0_5_0
status: Unaccepted release-bundle correction candidate
```

- [ ] Connected Network links allow explicit movement-conflict selection and persist; invalid/duplicate conflicts are rejected.
- [ ] Coordinated virtual signals never report both conflicting movements green, including vehicle amber and pedestrian clearance.
- [ ] Blocked crossing shows virtual red hold with reason; phase clock remains paused and resumes after protected 2 s clearance.
- [ ] Emergency route requires configured conflicts; destination priority is bounded, cancelled on expiry/removal and preserves pedestrian safety.
- [ ] Camera AI observations still feed their own crosswalk controllers, with stale/partial source safeguards.
- [ ] Version/structure guard passes and finds current `PATCH_0_5_14.md`, three candidate documents, changelog section and only `0_5_14` in frontend version constant.
- [ ] `CameraDetectionView` TypeScript typecheck passes with missing `cameraStatus`; preview correctly falls back to frame or 1280×720 dimensions.
- [ ] Vite build, backend `/health` and startup/smoke pass on Windows.
- [ ] Existing camera AI preview, crosswalk independent simulation signals and Network virtual-only emergency priority do not regress.
- [ ] Owner confirms PASS; accepted baseline remains `0_5_0` until then.

## Previous 0_5_13

Two null-safe preview resolution reads were patched, but the candidate's incomplete release files prevented running the normal startup validation.

---

# V0512 Camera-to-Crosswalk Observation Candidate

```text
version: 0_5_12
previous_version: 0_5_11
passed_baseline: 0_5_0
status: Unaccepted candidate — full Windows and hardware tests pending
```

- [ ] Opt-in one-way emergency route defaults Off, confirms ambulance in two distinct frames across ≥1s, and requests only the configured next-crosswalk virtual controller.
- [ ] Emergency priority is bounded and never bypasses pedestrian clearance or amber/all-red transition.
- [ ] Ambiguous multiple routes are rejected; no physical LED outputs.
- [ ] Background inference routes assigned Side A/B frames into the matching independent controller without opening Network.
- [ ] Multi-camera region average, single-view, zero-objects and missing/stale/model-switched cases.
- [ ] Class-specific conditions use physical Crosswalk regions; untyped regions do not claim waiting/crossing/queue metrics.
- [ ] AI source/coverage and per-class counts visible in Network, selectable physical Crosswalk regions in Live Signal Adjustments.
- [ ] Real ESP camera AI drives only virtual, clearly labeled software signals; missing/stale streams stop the virtual preview.
- [ ] Existing signal transition limits, API envelopes, legacy traffic/AI pipeline, Network drag/persistence, camera switching and non-simulation mode unchanged.
- [ ] Focused Python tests, full Windows runner, TypeScript/Vite, backend startup/smoke and owner PASS.

## Previous V0511 Independent Controllers

# V0511 Independent Controllers Candidate

version: 0_5_11; previous_version: 0_5_10; passed_baseline: 0_5_0.

- [ ] Each saved Crosswalk has a separate simulated controller with isolated runtime/test state.
- [ ] Network shows independent states from new read-only API; no fabricated physical signal state.
- [ ] Crosswalk addition/deletion updates controller registry; simulation off clears simulation states.
- [ ] Network links report neighbors only. Coordination remains disabled; movement conflicts are not configured.
- [ ] Existing signal phases/protected transitions, camera, global simulation, Network drag/save and rule settings regressions pass.
- [ ] Full Windows runner, frontend build, API smoke and owner PASS. Baseline stays 0_5_0.

# V0510 Network Signal and Adjustment Checklist (partial)

```text
version: 0_5_10
previous_version: 0_5_9
passed_baseline: 0_5_0
status: Partially implemented; full validation and owner PASS pending
```

- [ ] Traffic Light Settings and Live Signal Adjustments appear under Traffic; existing Signal Control page still works.
- [ ] Default signal phase time saves/reloads, respects minimums/maximums, preserves profile scenarios.
- [ ] New adjustment templates are disabled by default; enabling supported class/zone or crowd rules persists without overwriting unrelated settings.
- [ ] Pedestrian near-end rule checks crossing count and phase-remaining seconds; no unsafe clearance shortening or conflicting vehicle green.
- [ ] Network cards show live simulator source-scoped signal colours/countdown and active adjustment label only for observed crossing; other crossing lamps are unavailable.
- [ ] Directly linked neighbours display advisory-only adjustment notices; no false crosswalk phase or controller claim.
- [ ] Existing Network drag/links/persistence, simulation, traffic state, tracking, camera operations and safety regression PASS.
- [ ] Full Python/TypeScript/Vite/startup/smoke/Windows/manual checks and owner PASS; baseline `0_5_0` stays unchanged.

## Previous V059 Global AI and Preview Candidate Checklist

```text
version: 0_5_9
previous_version: 0_5_8
passed_baseline: 0_5_0
status: Global AI multi-camera preview candidate
```

- [ ] Traffic section above AI, AI Models / Camera AI Preview in AI, Settings page absent.
- [ ] Upload/import .pt without overwrite, load one running model, set default, delete inactive model; active deletion rejected.
- [ ] Global confidence and model interval slider (100–2000 ms) persist after app restart; no duplicated confidence slider in Preview.
- [ ] Active saved ESP and simulated camera frames are independently inferred with one global model. No stale frame queues; missing cameras do not show stale observations.
- [ ] Preview switches among saved cameras without changing global selected source. Boxes/labels/confidence show on exact source image; saved Side A/B polygon aligns, per-class per-region counts appear separately and do not count an object twice in overlapping regions.
- [ ] Existing camera, crosswalk, legacy traffic analytics, Network, dataset capture and signal safety operate unchanged.
- [ ] Full Python regression, TypeScript/Vite, backend startup/`/health`, live smoke and owner hardware/UI acceptance; accepted baseline remains `0_5_0`.

## Previous V058 AI & Network Drag Candidate Checklist

```text
version: 0_5_8
previous_version: 0_5_7
passed_baseline: 0_5_0
status: AI workspace and Network drag connections candidate
```

- [ ] Camera Settings above AI group, with Camera AI Preview and AI Models only in AI group.
- [ ] Preview shows real selected camera inference, labeled boxes and class filters; no fake fallback detections or duplicate model mutation controls.
- [ ] AI Models loads/unloads/selects/defaults saved models and persists validated default detection confidence through existing runtime settings.
- [ ] Network connects only by dragging edge label to a different crossing edge label (or keyboard activation); preview line, cancel, duplicate rejection, and saved exact label-to-label lines work.
- [ ] Moving crossing boxes uses the title drag; previous connections/save API remain intact.
- [ ] Full Python regression, TypeScript/Vite build, backend startup/smoke and Windows visual acceptance pass; baseline remains `0_5_0`.

## Previous V057 Crossing-first Network Checklist

```text
version: 0_5_7
previous_version: 0_5_6
passed_baseline: 0_5_0
status: Crossing-first Network workspace candidate
```

- [ ] Crosswalks navigation above Network; saved crossing creates a Network box without another add action.
- [ ] Connections use numbered edges 1–4, can be removed, and remain after Save/reload; draggable positions persist.
- [ ] Deleting a crossing removes its Network links; invalid graph data rejected without overwriting prior config.
- [ ] Camera health on each box, selected-source-only AI observations, clear unavailable status for unobserved crossings.
- [ ] Legacy junction management accessible in Advanced section; no signal-control changes.
- [ ] Full Python offline regressions, frontend TypeScript/build, live backend smoke, responsive UI and owner PASS.

## Previous V056 Shared Physical Region Checklist

```text
version: 0_5_6
previous_version: 0_5_5
passed_baseline: 0_5_0
status: Two-view region geometry candidate
```

- [ ] Region 1 uses one name on A/B, top polygon on A and bottom polygon on B.
- [ ] Side switching retains logical region selection; no backend ID field is shown.
- [ ] Save/reload retains both polygons and shared name; legacy saved regions remain valid.
- [ ] Per-camera inferred counts have distinct camera-region IDs and a shared physical-region ID, without double-counting.
- [ ] Run full offline regression suite, frontend TypeScript/build, live smoke/startup and Windows visual acceptance. Baseline remains `0_5_0`.

## Previous V055 Regression Alignment Candidate Checklist

```text
version: 0_5_5
previous_version: 0_5_4
passed_baseline: 0_5_0
status: Camera/region regression alignment candidate
```

- [ ] Camera Settings structural regression accepts the current paired simulator API call and hidden-controls wiring.
- [ ] Historical V0418 regression verifies Side A/B switching clears stale polygon selection.
- [ ] Full offline regressions, frontend build, live backend smoke and visual confirmation on Windows.
- [ ] No camera/simulation/region persistence or signal behavior changed; owner PASS pending.

## Previous V054 Candidate Checklist

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
