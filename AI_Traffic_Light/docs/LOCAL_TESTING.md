# V0510 Network signal and live-adjustment candidate (partial)

```text
version: 0_5_10
previous_version: 0_5_9
passed_baseline: 0_5_0
status: Partially implemented signal controls and Network indicators candidate
```

## Validate on Windows

- Run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1"` without `-ChangedTests` from the repo root. Check structural gate, focused `test_v0510_signal_adjustments.py` and `test_v0510_signal_navigation.py`, all regression tests, TypeScript/Vite, health/smoke and startup.
- Under Traffic, open Traffic Light Settings; change the active profile's vehicle green, pedestrian WALK and amber default times within displayed minimum/maximum constraints, Save, reload and verify persistence. Check invalid changes are blocked; original all-red protected phases remain enforced.
- Open Live Signal Adjustments: templates are disabled until enabled. Configure a compatible active legacy zone for ambulance/wheelchair classes and verify active detector support, or use a controlled preview/test scenario. Test crowd thresholds and a crossing still occupied with 3 seconds of clearance remaining, verify protected extension and no conflicting green. Confirm dry-run and stale-data behavior and no emergency flashing-green command.
- Network: select simulator and assign a saved matching simulation camera to Crosswalk A, confirm vehicle and pedestrian bulbs match the active phase and countdown. Other Crosswalk B without independent signal must show unavailable. Trigger a rule at A while A↔B is connected; B displays `not applied here` advisory, **not** a changed signal. Confirm dragging edge labels and crosswalk titles still works, and Save/reload retains links.
- Test with simulation off: indicators display unavailable and do not depict hardware light state. Check existing Signal Control pages, Crosswalk Region Editor, camera preview, network topology and basic signal controller remain unchanged.
- **Explicitly pending:** verified movement conflict topology, independent per-crosswalk controllers and actual adjacent signal coordination; this candidate cannot alter neighbour phase times and cannot command physical traffic signals.
- Full local/Windows validation and owner PASS required. Accepted baseline remains `0_5_0`.

## Previous V059 Global AI and Preview Candidate

```text
version: 0_5_9
previous_version: 0_5_8
passed_baseline: 0_5_0
status: Global AI Models and multi-camera preview candidate
```

## V059 Windows validation

- From repository root run the full `scripts/update_test_run.ps1` (without `-ChangedTests`). Check Python/structure regressions, TypeScript/Vite build, backend startup `/health`, smoke, and app launch.
- Confirm sidebar Traffic precedes AI, AI Models precedes Camera AI Preview, and Settings page is absent. Other navigation/Camera Settings and Traffic behaviors should be unchanged.
- AI Models: upload a small valid `.pt` model with a unique ID; confirm list, load/activate, default, and persist. Refuse duplicate IDs, invalid IDs, empty/oversized files; refuse deletion of the active model. Delete an inactive model and confirm only its run directory is removed. Invalid model weights may upload but must show an activation error.
- Set global confidence and inference interval slider (100–2000 ms), save, refresh app and verify settings remain. Preview should not offer a confidence slider.
- With saved simulated pairs and a valid loaded model, select A, B, C and D independently in Camera AI Preview. Verify frame matches source, class/confidence boxes align, each region uses the correct Side A/B saved polygon, counts appear in the separate region table (not drawn over camera image), and switching preview does not change the selected camera in Camera Settings.
- Connect and stream 2+ ESP cameras; verify inference on both while one is selected, the inactive saved stream still contributes preview detections, disconnected/stale streams show unavailable and do not inherit detections from other cameras. Target frequency depends on CPU/GPU and total camera count. With no model loaded, show no detection boxes; do not fabricate counts.
- Check legacy selected-source `/api/inference/detections`, `/api/traffic/state`, Network, dataset capture, manual camera switching, signal transitions and crosswalk region save/reload. No multi-camera identity fusion or physical signal authorization is introduced.
- Owner PASS pending; accepted baseline stays `0_5_0`.

## Previous V058 AI Group and Network Drag Candidate

```text
version: 0_5_8
previous_version: 0_5_7
passed_baseline: 0_5_0
status: AI workspace and Network drag connections candidate
```

## V058 Windows validation

- Run the full `scripts/update_test_run.ps1` without `-ChangedTests`; check structure and version gate, all Python tests, TypeScript, Vite build, backend health and smoke.
- Confirm Operate lists Camera Settings/Camera Diagnostics before the new AI sidebar group, which contains exactly Camera AI Preview and AI Models. The old AI Detection and Model Registry sidebar entries must not appear elsewhere.
- Camera AI Preview: with a real or connected simulation camera and a loaded model, show the selected camera frame, detection boxes and class filtering. Without a frame, show a clear camera-unavailable message with no fake detections; no model deletion/load controls or automatic model loading on the preview.
- AI Models: list existing trained models, load/set default/unload, change default confidence 0.01–1.00, save it and verify it persists after refresh; backend errors should appear without losing UI state.
- Network: press on Crossing A numbered edge 2, drag until the preview line reaches Crossing B edge 4, release and confirm the link appears at the edge label endpoints. Save network, reload, verify persistence. Drag a crossing title separately; canceled release or same-crossing release must add no connection. Test duplicate rejection and keyboard source/destination activation.
- Existing Crosswalk creation, Region Save, camera assignments, simulation hiding toggle, junction advanced configuration and signal safety must remain unchanged. Owner PASS pending, accepted baseline `0_5_0`.

## Previous V057 Crossing-first Network Candidate

```text
version: 0_5_7
previous_version: 0_5_6
passed_baseline: 0_5_0
status: Crossing-first Network workspace candidate
```

## V057 Windows validation

- Run the full `scripts/update_test_run.ps1` (no `-ChangedTests`) including structural guards, all offline regressions, frontend typecheck/build, backend startup and live smoke.
- Confirm Crosswalks appears above Network and the sidebar no longer labels the page Junction Network.
- In Crosswalks, add and **Save** A and B. Open Network: both boxes must appear automatically. Save another crossing; after the Network page refresh, the new box appears.
- Select A and edge 2, connect to B and edge 4. Drag both boxes, Save network, reload and verify links/positions persist. Remove a link and verify its removal. Delete a crossing in Crosswalks, save and confirm its Network links/position are cleaned.
- Verify active-source-only region observations, correct camera stream/offline state, narrow-viewport map scrolling, and existing advanced junction controls. Connections are metadata, not traffic commands.
- Owner PASS pending; baseline remains `0_5_0`.

## Previous V056 Shared Physical Region Candidate

```text
version: 0_5_6
previous_version: 0_5_5
passed_baseline: 0_5_0
status: Two-view region geometry candidate
```

## V056 validation

- Run the full updater without `-ChangedTests` to check **all** offline regressions, release consistency, frontend TypeScript/build, live smoke and startup.
- Crosswalks → Edit regions: Add Region 1 on Side A and move its vertices to the top; switch to Side B, keep Region 1 selected, move the same region's vertices to the bottom. Return to Side A: its polygon must remain at the top. Change the name and confirm it is the same on both sides.
- Select Save regions, navigate away/reload, confirm the shared name and both independent polygons persist. No backend ID input should appear.
- With a trained model and an assigned active camera, inspect `GET /api/traffic/state` → `crosswalk_region_counts`. The A or B observation should carry the same `physical_region_id` but distinct `camera_region_id`, and only the active source produces counts. Do not add the counts to infer unique objects.
- Confirm old shared and side-scoped regions still load, source switching does not leak counts, and simulator toggles stay hidden by default.
- Owner PASS and hardware validation pending; stable baseline `0_5_0`.

## Previous V055 Regression Alignment Candidate

```text
version: 0_5_5
previous_version: 0_5_4
passed_baseline: 0_5_0
status: Camera/region regression alignment candidate
```

## V055 validation

- Run the full updater (no `-ChangedTests`) once to verify all existing offline tests, in particular `test_camera_settings_page_structure.py` and `test_v0418_camera_region_ui.py`.
- Confirm TypeScript, frontend build, backend `/health`, live smoke and PC Studio startup.
- Manually verify Simulation Camera Pair 1/2 choices behind the brand toggle and independent Crosswalk Side A/B region editing and Save regions.
- No application runtime changes; awaiting owner PASS.

## Previous V054 Camera-Scoped Regions Candidate

```text
version: 0_5_4
previous_version: 0_5_3
passed_baseline: 0_5_0
status: Camera-scoped counting candidate
```

Test Side A/B independent polygons, rename IDs and Save regions; verify GET /api/traffic/state crosswalk_region_counts under trained inference for active camera. Run frontend typecheck/build and smoke. Owner PASS pending.

## V053 Release Consistency Candidate

```text
version: 0_5_3
previous_version: 0_5_2
passed_baseline: 0_5_0
status: V052 release metadata repair candidate
```

## V053 acceptance

- Verify update runner structure/version validation, frontend typecheck/build, backend smoke and Region Editor Save regions persistence.
- V052 Save regions implementation remains unchanged. Owner PASS pending.

## V0501 acceptance

- Run updater with `-ChangedTests`; verify frontend build, smoke and startup.
- On startup simulation options and Experiments are hidden. Click or keyboard-activate AI Traffic Light brand to reveal them; toggle back to hide them. When hiding Experiments, return Dashboard.
- Confirm ESP controls, camera states, saved Side A/B assignments, Regions and existing simulator state are unchanged. Active synthetic inputs remain correctly identified.
- Windows owner PASS pending; stable baseline remains `0_5_0`.

## V050 archive


```text
version: 0_5_0
previous_version: 0_4_24
passed_baseline: 0_5_0
status: Owner-accepted stable release
```

## V050 stable release verification

- The owner explicitly confirmed PASS for V0424 and requested the next stable version. V050 promotes that accepted implementation without new runtime features or code changes.
- Confirm the app reports `0_5_0 Stable` and the Crosswalk layout still shows Side A / Side B camera selectors side by side, with each source state in its own section.
- Verify the previously accepted region translucency, simulation cameras and crosswalk configuration are unchanged. The Windows updater/test runner remains available for optional revalidation; its results have not been observed here.
- Accepted baseline: `0_5_0`.

## Historical V0424 and earlier checks (archival)


```text
version: 0_4_24
previous_version: 0_4_23
passed_baseline: 0_4_14
status: Crosswalk camera-side layout candidate
```

## V0424 Crosswalk camera selector acceptance

- Run `scripts/update_test_run.ps1 -ChangedTests`; verify focused Crosswalk regression, frontend typecheck/build, backend smoke and startup.
- Select a crosswalk. Its Crosswalk layout must show a left Side A and right Side B selector, each directly followed by its current camera status, above the existing schematic.
- No duplicate Side A/B status rows and no bottom Side B selector remain. Narrow widths should stack Side A then Side B without horizontal overflow.
- Select cameras and save/reload; confirm both assignments and statuses persist/update normally, missing-camera warnings work, and the existing simulation preview/region controls are unchanged.
- Candidate V0424 requires Windows visual acceptance; passed baseline remains V0414.

## Historical V0423 and earlier checks (archival)


```text
version: 0_4_23
previous_version: 0_4_22
passed_baseline: 0_4_14
status: Translucent region overlay candidate
```

## V0423 translucent region appearance acceptance

- Run `scripts/update_test_run.ps1 -ChangedTests`, verify the focused region regressions, frontend typecheck/build, backend smoke and startup.
- Open Crosswalks → Edit regions with a simulation camera: unselected regions show a light 10% mint tint and the selected region shows a 22% pale cream tint. Both allow the video beneath to remain visible.
- The selected pale-yellow dashed outline remains 6px and fully opaque; numbered vertices drag, Side A/B toggles work and saving/reloading leaves coordinates unchanged.
- The hidden legacy editor uses the same fill opacity with its existing 7px selected outline. Live AI/simulation region outlines stay unfilled; dataset boxes stay unchanged.
- V0423 awaits owner PASS; accepted baseline remains V0414.

## Historical V0422 and earlier acceptance notes (preserved for reference)

```text
version: 0_4_22
previous_version: 0_4_21
passed_baseline: 0_4_14
status: Responsive text layout and clear selected-region outline candidate
```

## V0422 responsive text and selection acceptance

- Run the standard single-command updater with `-ChangedTests` and confirm regressions, frontend typecheck/build, backend smoke and startup.
- Resize the desktop browser to wide, medium and narrow widths; inspect the sidebar, page/panel headers, buttons, Saved cameras, and status pills. Text should wrap without clipping, with consistent alignment and readable font sizes.
- Inspect Junction Network camera IDs and link names (including long identifiers), Signal Control scenario descriptions, and Simulation Experiment scenarios, tabs and results. Full wording must be readable; on short-height screens, scroll to see all experiment content. Data tables may scroll horizontally.
- In Crosswalks → Edit regions, selected and unselected polygons must have no interior tint; selection should be indicated by a brighter, fully opaque, thicker dashed pale-yellow border with existing draggable vertices.
- Confirm the V0421 second simulation-camera pair remains selectable/usable and saved region geometry is unchanged.
- V0422 remains unaccepted until owner PASS. Accepted baseline stays V0414.

## V0421 two-pair simulation acceptance

- Run the standard one-line update/test runner with `-ChangedTests`; verify both backend camera regressions, frontend TypeScript/build and startup smoke.
- In Camera Settings → New camera → Simulation pair, ensure Pair 1 is saved if absent, then use `Add second simulation pair`. Four saved simulated camera IDs should appear: `simulation_camera`, `simulation_camera_b`, `simulation_camera_c`, `simulation_camera_d`.
- Select each saved camera and check its preview. Pair 1's two views are vertical mirrors; Pair 2 is the same synthetic intersection from a horizontally reflected viewpoint and its mirror. These are two camera pairs on one simulator, not two independent simulations.
- In Crosswalks, assign C/D to the two camera sides of a crosswalk and save/reload. Do not overwrite existing assignments.
- Delete Pair 2 through either C or D and verify Pair 1 survives and continues simulating. Restore Pair 2, delete Pair 1 and verify Pair 2 survives. Physical ESP configurations must stay intact.
- V0422 supersedes V0420's selected translucent overlay; both selected and unselected region interiors remain clear.

## V0420 selected-region visual acceptance

- Run the standard one-line update/test/runner with `-ChangedTests`.
- In Traffic → Crosswalks → Edit regions, selected and unselected polygons have no interior fill. Selection is indicated by a thicker opaque pale-yellow dashed border and draggable numbered vertices.
- Toggle Side A/B and drag vertices to verify selecting/deselecting and geometry persistence. Normal Live AI region overlays should remain fully clear.
- Legacy Region Editor selected polygons use the same light translucent highlight. Dataset object boxes and simulation imagery are unchanged.
- Check TypeScript compilation, production build, live backend smoke, and app startup. V0420 remains a candidate until owner PASS.

## V0419 duplicate CSS rule regression verification

- Run the standard updater with `-ChangedTests` and verify the V0418 regression now inspects both the original cursor declaration and later camera-card background declaration.
- The earlier `assert "cursor: pointer;" in entry` should pass; confirm remaining selected tests, frontend typecheck/build, backend smoke and startup.
- V0418's camera selection, simulation image, region Side A/B buttons, transparency and Simulation active badge alignment are unchanged; continue their visual acceptance.
- Owner-accepted baseline remains V0414; V0419 is a candidate until Windows PASS.

## V0418 camera and region acceptance

- Run the standard one-line updater and confirm the new and historical regressions, frontend TypeScript/build, backend smoke and app startup.
- In Camera Settings → Saved cameras, click a saved ESP or simulation camera card. It should select the camera and update the active preview without duplicating camera-selection services. Verify keyboard focus and busy protection.
- Start PC simulation: the image should show cars and people on the street and crosswalk, **without** text banners, STOP text, traffic signal housings or buses. The simulation signal-state API and safe vehicle/pedestrian timing remain functional.
- In Crosswalks → Edit regions, toggle Side A and Side B with buttons and confirm the correct source preview. Selected regions retain contrasting dashed outlines and numbered drag handles, but normal/selected interiors show the image without translucent fill.
- Check the Simulation active status pill: text should be visually centered. Verify the backup file and regression notes exist at `docs/backups/V0417_PRE_V0418_CODE.md`.
- Accepted baseline remains V0414; V0418 is unaccepted until Windows PASS.

## V0417 transparent region polygon validation

- Run the standard one-line updater and wait for offline regressions, frontend typecheck/build, live smoke and startup.
- In Traffic → Crosswalks → Edit regions, normal and selected region polygons should have no interior fill. Selected polygons should stand out through a thicker warning-colored dashed outline and numbered draggable vertices while remaining completely transparent; unselected regions retain thinner mint outlines.
- In Live AI, regions should overlay live/simulated cameras as unfilled outlines; labels and detections remain legible.
- Legacy Region Editor polygon interior should be transparent for normal and selected states. Dataset Review bounding boxes retain their current display.
- Confirm light and dark modes and saved region geometry are unchanged.

## V0416 Regions wording and navigation validation

- Run the standard one-line updater with `-ChangedTests`; confirm focused Python regressions, TypeScript, build, backend smoke and app startup.
- Traffic sidebar must include Junctions and Crosswalks but no empty Zones page. The Crosswalks → Edit regions workflow must still open its quadrilateral region editor.
- Live AI must show Regions instead of Zones; Signal Control and Traffic Analytics use Region/Regions labels. No visible legacy Zone Editor terminology should remain.
- Verify camera overlays, configured region selection and scenarios still work with saved zone IDs. Internal `zone_id` and `/api/zones` keys deliberately remain unchanged.
- Previous candidate V0415 darker canvas remains included. Owner-accepted stable baseline is V0414.

## V0415 dark canvas validation

- Run the normal single-command updater with `-ChangedTests`.
- Confirm the dark main canvas is `#444557`, slightly darker than accepted V0414 `#4D4E61`; panels, quiet sidebar, mint `#57FFED`, and light mode should remain unchanged.
- Confirm the existing palette and design-structure regressions pass with the new background token; verify TypeScript/frontend build, startup, and live backend smoke.
- Accepted stable baseline is V0414. V0415 remains a candidate until owner PASS.

## V0414 test ownership correction

- Run the normal single-command updater with `-ChangedTests`.
- The previously failing historical `test_v0409_palette_layout.py` should retain palette and junction checks without demanding a removed navigation-heading token.
- `test_v0413_quiet_navigation.py` remains the single focused regression for current sidebar appearance.
- Confirm frontend TypeScript check, production build, backend live smoke and app startup. The workspace CSS and UI are unchanged by V0414.

## V0413 quiet navigation acceptance

- Run the standard one-line update/test/run command; check frontend typecheck/build and live smoke.
- Sidebar group headings (Operate, Traffic, Data & Models) should be small muted uppercase labels with a subtle horizontal divider, not dark boxes with mint borders.
- Selected page should use a solid neutral slate row with bright text and no mint bar or dot; hover should be restrained. Keyboard focus still needs a visible mint outline.
- Test light/dark appearance, navigation across pages, compact window width and preservation of other selection indicators (camera, tabs, toggles).
- The sidebar brand/title remains boxed; Junction Network card, camera and simulation behavior are unchanged.

## V0412 CSS selector regression correction

- Run the standard one-line update/test/run command from the repository root.
- The `test_v0411_junction_card_layout.py` regression should use the last `.junction-node-alerts` rule, not its earlier grouped-selector declaration, and pass.
- Continue to the Windows frontend TypeScript check, production build, startup and live backend smoke.
- Visually confirm the V0411 Junction Network title bar, centered information and four-sided labels. No runtime styling was changed in V0412.

## V0411 Junction Network card acceptance

- Run the standard one-line updater/test/runner.
- On Junction Network, each node should have an independent full-width title bar with junction name and ID; drag anywhere on the title bar.
- Verify traffic vehicle/pedestrian load, camera count, current phase, events and warnings remain centered and fully readable in the main content area.
- Verify numbered edge controls 1–4 sit on the four corresponding sides of the content area, below the title bar, without overlapping information.
- Test very long junction names, IDs, long phase text and narrow windows: fonts adapt to card width, text wraps and node height grows rather than truncating or hiding content.
- Check edge click/selection, crosswalk assignment, drag offset, light/dark themes and frontend TypeScript/build. No hardware required for visual checks.

## V0410 TypeScript repair validation

- Run the standard single-line update/test/run command from the repository root.
- Verify the Camera Settings static regression, TypeScript typecheck (`npm run typecheck`) and frontend production build (`npm run build`) pass.
- Add an ESP32 camera and confirm Save/Connect controls still reflect streaming, busy and missing IP/source ID.
- Verify adding a simulation pair remains available as a separate action. Camera simulation/ESP routing is unchanged.
- Continue V0409 slate/mint and Junction Network visual acceptance, plus live backend smoke.

## V0409 visual acceptance

- Run the standard one-line updater/test/runner from the repository root.
- In Windows dark appearance, confirm a `#4D4E61` canvas, separate dark sidebar, boxed brand/title area, navigation group header strips, raised opaque panels, legible text and `#57FFED` interactive emphasis.
- Confirm light mode still uses the existing light surfaces and deep teal (`#006F66`).
- In Junction Network, inspect junctions at desktop and narrow widths. Edge buttons 1–4 must be inside their respective cards, readable, selectable, and never cover the ID, title, camera count, status, or drag handle.
- Check hover/selection, semantic state pills, forms and vehicle/pedestrian chart series in Camera Settings, Crosswalks, Live AI, Traffic Analytics and Simulation Experiments.
- Validate backend `/health`, the live startup smoke and frontend build. Hardware-only tests remain separate.

## V0408 Windows port-8000 acceptance

- Run the existing one-line update/test/run command. Its preflight regression now executes the real process-identification predicates against Windows process fixtures.
- Port 8000 with system-Python Uvicorn child and verified AiTL virtualenv launcher must restart; unknown or unrelated Python owners must remain protected.
- Confirm backend `/health`, live smoke, frontend startup, and the existing UI behavior. The parent PowerShell host must remain open.
- Hardware tests remain manual. V0408 is a candidate until the owner confirms PASS.

## V0407 backend port-owner validation

- Run the existing one-line update/test/run command. It must keep other processes safe on ports 5173 and 8000.
- If 8000 is held by this project's Uvicorn `--reload` worker, the runner should identify its verified virtualenv parent and restart its process tree without closing unrelated PowerShell windows.
- If 8000 is owned by an unrelated Python program, the runner must refuse to terminate it.
- Verify `/health`, live backend smoke, frontend launch and previously passing Junction Network regression.
- No real hardware required. Owner Windows validation and PASS are pending.

## V0406 test alignment

- Run the existing one-line update/test/run command from the repository root.
- The Junction Network static regression must validate the current simulation/physical camera mode label and the editable primary-camera selector.
- All pending V0405 dark/light theme, frontend typecheck/build and smoke checks remain required.

## V0405 theme and selection acceptance

- From the existing project root run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests`.
- In Windows dark appearance, primary buttons, focus rings, active navigation and selected/toggled controls should use mint `#57FFED` with dark text on filled mint buttons.
- In light appearance, the same interactions should use legible dark teal `#006F66` instead of pale mint on white.
- Inspect Dashboard navigation, Camera Settings selected camera status, Crosswalk list, Junction Network selected edges, Traffic Analytics, Signal Control, Simulation Experiments, Dataset Review and Live AI checked class filters.
- Confirm every selection is also indicated by a dot, underline or border, not color alone; hover and keyboard focus must remain distinct from selection.
- Backend/ESP behavior is unchanged. Frontend build, full startup smoke and owner visual PASS are still required.

## V0404 startup gate repair

- Run the existing one-line update/test/run command from the repository root.
- The structure gate should accept the semantic dark base `#0E1725` instead of demanding `#121212`.
- The V0403 visual regression now checks acceptance of the current palette and rejection of malformed base values.
- Continue the pending V0403 frontend build, backend smoke and light/dark visual acceptance below.

## V0403 visual acceptance

- From the repository root, run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests`.
- Inspect Dashboard, Camera Settings, Crosswalks, Junction Network, Live AI, Dataset Review, Traffic Analytics, Simulation Experiments and Settings in **both Windows light and dark appearance**.
- Confirm legible text, neutral panels, visible input boundaries, clear primary actions and selected navigation, and correct selected tab / segmented view state.
- Test keyboard Tab and simulation panel Left/Right/Home/End navigation. Confirm no clipped layout at typical 1280px and 1920px desktop widths.
- Real/simulation camera and saved data behavior should be unchanged; full frontend build and live smoke must pass before owner PASS.

## V0402 acceptance

- The Crosswalk structure test must recognize the mirrored simulation pair and numbered edges.
- All V0401 functional validation steps below remain required.

## V0401 acceptance

- From repository root run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests`.
- Camera Settings → New Camera → Simulation pair adds exactly two virtual cameras. Select either; Side B must be vertically mirrored.
- Crosswalks → Assign simulation pair sets sides A/B; Save changes and confirm both side previews. Four numbered edge labels appear on the schematic.
- Junction Network edge labels do not obscure card text; dragging from the header does not jump the node centre to the pointer.
- Dashboard, Camera Settings and Crosswalks show no test-ready badges; legacy Camera Sources/Zone Editor disappear from navigation; Zones opens blank.
- Verify real ESP selection and existing crosswalk/junction saved settings are unchanged. Full backend/frontend live smoke and user PASS remain required.


## V0400 startup regression check

- Run `python scripts/test_camera_settings_page_structure.py`: assert simulated previews use the selected simulation branch and physical ESP previews explicitly exclude simulation.
- Run `scripts/update_test_run.ps1 -ChangedTests` from Windows; verify previously blocked startup proceeds through frontend typecheck/build and live smoke.

## Camera and network focused regression

- Create a simulation camera under Camera Settings → New camera and confirm it is selected, previewed and can be removed/re-added without IP or ESP.
- Connect junction 1 edge 2 to junction 2 edge 4; Save network, refresh, and verify the endpoint IDs persist.
- Run `python scripts/test_remote_camera_multi.py`, `python scripts/test_camera_settings_page_structure.py`, `python scripts/test_junction_network_frontend_structure.py`, and `python scripts/test_intersection_network.py`.

## Previous startup regression checks

- Run `python scripts/test_camera_settings_page_structure.py` and `python scripts/test_crosswalks_frontend_structure.py` to confirm both pages remain included in `CAMERA_POLL_PAGES` regardless of neighboring pages.
- Run `scripts/update_test_run.ps1 -ChangedTests` from Windows to verify the full startup pipeline. The original V0324 junction-edge owner checks below remain pending.


## Focused checks

- `python scripts/test_intersection_network.py`: backwards-compatible N/E/S/W defaults, save/reload mappings, duplicate/invalid-reference rejection and untouched signal/controller mapping.
- `python scripts/test_junction_network_frontend_structure.py`: four clickable map labels, edge inspector, typed keys, crosswalk retrieval and missing assignments.
- `python scripts/check_structure.py`, frontend `npm run typecheck`, `npm run build`.

## Owner test

1. Create several named crosswalks in Traffic → Crosswalks.
2. Open Traffic → Junction Network; every card should display N/E/S/W edge buttons, including on unassigned cards.
3. Click each edge and select one crosswalk. Change or clear a mapping. Confirm one crosswalk cannot be assigned to multiple edges.
4. Save network and restart PC Studio; mapping persists while existing cameras, junction dragging, topology links and simulation remain functional.
5. Delete a referenced crosswalk in Crosswalks. Return to Junction Network and click **Refresh crossings**: its ID should be retained and marked Missing, with an option to clear/reassign.
6. Run the full Windows `scripts/update_test_run.ps1` for complete regressions, typecheck/build, backend smoke and UI launch.

No physical hardware is needed for mapping itself. Full owner PASS is pending; baseline stays `0_4_0`.
