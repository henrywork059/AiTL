# Local Testing — V0327

```text
version: 0_3_27
previous_version: 0_3_26
passed_baseline: 0_3_11
status: Camera Settings preview regression assertion repair candidate
```

## V0327 startup regression check

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

No physical hardware is needed for mapping itself. Full owner PASS is pending; baseline stays `0_3_11`.
