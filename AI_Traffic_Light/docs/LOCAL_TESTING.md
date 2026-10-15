# Local Testing — V0409

```text
version: 0_4_9
previous_version: 0_4_8
passed_baseline: 0_4_0
status: Slate and mint design alignment candidate
```

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
