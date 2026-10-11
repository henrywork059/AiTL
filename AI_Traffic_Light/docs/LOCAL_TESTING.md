# Local Testing — V0320

```text
version: 0_3_20
previous_version: 0_3_19
passed_baseline: 0_3_11
status: Crosswalk configuration candidate
```

Run `python scripts/test_crosswalks_service.py`, `python scripts/test_crosswalks_frontend_structure.py` and `python scripts/check_structure.py`. Build frontend with `npm run typecheck` and `npm run build`.

Check Traffic → Crosswalks: add multiple entries, change labels/locations, assign two different saved cameras, save and reload, delete one and persist. Test missing/deleted ESP profiles and offline status. Verify that only two distinct camera slots exist on opposing pedestrian approaches and that the drawing is a schematic, not real camera geometry.

Run full Windows `scripts/update_test_run.ps1` and confirm PASS after actual application validation. Baseline `0_3_11` remains unchanged.
