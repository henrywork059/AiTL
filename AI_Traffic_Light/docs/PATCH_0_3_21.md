# PATCH_0_3_21 — Crosswalk schematic orientation

Version: `0_3_21`  
Previous candidate: `0_3_20`  
Passed baseline: `0_3_11` (unchanged)

## Scope

- Correct the Crosswalks SVG so seven horizontal white zebra stripes span the vertical crossing corridor between pedestrian Side A (top) and Side B (bottom).
- Align the two vertical dashed path guides with the crossing; retain cameras A/B, road, arrows, source assignment, save/reload and all other UI behavior.
- Update the diagram's accessible description and focused frontend structure regression.
- No changes to backend APIs, saved crosswalk schema, camera firmware, inference or signal control.

## Validation

- Focused static layout/geometry and crosswalk UI wiring assertions.
- Run `python scripts/test_crosswalks_frontend_structure.py`, `python scripts/check_structure.py`, frontend `npm run typecheck` / `npm run build`, and full Windows runner for acceptance.
