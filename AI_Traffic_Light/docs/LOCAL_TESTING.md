# Local Testing — V0323

```text
version: 0_3_23
previous_version: 0_3_22
passed_baseline: 0_3_11
status: Crosswalk regions and shared simulation candidate
```

## Tests

- `python scripts/test_crosswalks_service.py`: older JSON compatibility, add/edit/delete, valid and invalid quadrilaterals, rejected invalid saves preserving previous persisted data.
- `python scripts/test_crosswalks_frontend_structure.py`: region workspace and pointer handlers, camera switching/preview guard, app simulation prop wiring, existing crosswalk schematic.
- `python scripts/test_junction_network_frontend_structure.py`: shared global simulator indicator/control.
- `python scripts/check_structure.py`, frontend `npm run typecheck`, `npm run build`.

## Hands-on validation

1. Add two crossings; save/reload and confirm each retains its own separate region collection.
2. Open Edit regions; create a quad and drag each of four handles; rename, delete, create a second; Back → Save changes → reload.
3. Select camera Side A, then Side B; confirm region polygons persist unchanged. For physical preview, ensure selected camera is streaming and choose Select camera for preview.
4. Toggle simulation from Junction Network, then inspect Crosswalks/region editor and Camera Sources: one shared simulated feed, physical ESP stream pause. Switch it off, ensure physical source is restored without falsely claiming simultaneous input.
5. Test self-intersecting, out-of-bounds and invalid region saves; verify validation error and no overwritten configuration.
6. Run the full Windows `scripts/update_test_run.ps1` and confirm backend health/smoke and frontend startup, then physical ESP behavior.

Hardware and UI tests require owner PC. Candidate `0_3_23` is not accepted until PASS; baseline remains `0_3_11`.
