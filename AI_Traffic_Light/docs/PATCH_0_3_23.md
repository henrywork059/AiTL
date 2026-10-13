# PATCH_0_3_23 — Crosswalk regions and shared simulation

Version: `0_3_23`  
Previous candidate: `0_3_22`  
Owner-confirmed passed baseline: `0_3_11` (unchanged)

## Changes

- Multiple crosswalks remain supported (maximum 32). A full-width region-editing workspace opens from each crosswalk while leaving its normal management page uncluttered.
- Regions are four-point, convex quadrilaterals stored once per crosswalk (maximum 24 per crossing). Start with a default quadrilateral, drag corner handles on a camera/simulation preview, rename or remove, then return and save the existing crosswalk configuration.
- One shared region set is overlaid for either selected camera side; coordinates are in a 1280 × 720 reference frame with no automatic camera perspective registration.
- Crosswalks and Junction Network expose the existing app-level camera simulation on/off switch. Simulation uses one camera source; physical ESP input pauses/resumes under existing camera service behavior.
- The crosswalk schema version stays 1 and older records missing `regions` load with an empty list. Existing request-ID/error envelope and atomic persistence remain unchanged.

## Testing

Run `python scripts/test_crosswalks_service.py`, `python scripts/test_crosswalks_frontend_structure.py`, `python scripts/test_junction_network_frontend_structure.py`, `python scripts/check_structure.py`, then frontend `npm run typecheck` and `npm run build`. Owner performs Windows full runner and hands-on camera/simulation validation before PASS.

This is a configuration/prototype UI feature, not simultaneous AI processing, active pedestrian prioritization, or physical road control.
