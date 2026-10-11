# PATCH_0_3_20 — Crosswalk configuration page

Version: `0_3_20`
Previous candidate: `0_3_19`
Passed baseline: `0_3_11` (unchanged)

## Implemented

- Traffic → Crosswalks page for creating, editing and removing named crosswalks and optional locations.
- Schematic road/pedestrian crossing with two opposite-side saved ESP camera assignments (Side A and Side B).
- Independent metadata store at `config/crosswalks.json`, using shared atomic JSON writes; typed GET/PUT API and offline regressions.
- Missing saved camera references remain visible and can be deliberately cleared or reassigned.

This is static configuration only: it does not implement simultaneous two-camera inference, pedestrian tracking, protected signal requests, or physical signal control. Camera registry, junction control and firmware are unchanged.

Validation: `python scripts/test_crosswalks_service.py`, `python scripts/test_crosswalks_frontend_structure.py`, structure checks, frontend build and owner runner.
