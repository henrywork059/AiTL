# Patch 0_5_6 — One physical region, independent Side A/B polygons

**Candidate:** `0_5_6`. **Previous candidate:** `0_5_5`. **Owner-passed baseline:** `0_5_0`.

- Region 1 is one logical, named physical area with a hidden internal ID. Side A and B use separately editable polygons; editing one cannot move the other's handles. The existing Save regions action persists both.
- Reuse existing crosswalk schema version 1, atomic PUT storage, camera selection, detection centre-in-polygon counting and source-specific result keys.
- New optional `vertices_by_side` contains independently validated camera A/B quadrilaterals; older `vertices` and `camera_side` records remain compatible and are not silently merged. Existing data is not overwritten during upgrade.
- Result `physical_region_id` groups two camera observations of one physical area. `camera_region_id` distinguishes each camera. Do not sum them as unique counts: no simultaneous dual-camera inference or identity matching is implemented.
- Update historical frontend structure tests and add one focused persistence/counting regression. No new dependencies or physical traffic control.

Run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1"` (full regression suite) from the repository root. Confirm Region 1 top on A, bottom on B, shared name, Save/reload, class counts for the currently inferred source and unchanged physical camera/simulation controls. Windows owner PASS pending.
