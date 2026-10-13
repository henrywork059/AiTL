# Local Testing — V0324

```text
version: 0_3_24
previous_version: 0_3_23
passed_baseline: 0_3_11
status: Junction edge crosswalk mapping candidate
```

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
