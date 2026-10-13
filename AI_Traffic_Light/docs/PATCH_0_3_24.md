# PATCH_0_3_24 — Junction edge labels and crosswalk assignment

Version: `0_3_24`  
Previous candidate: `0_3_23`  
Passed baseline: `0_3_11` (unchanged)

## Scope

- Add visible and clickable cardinal edge labels **N, E, S, W** around every junction card in Traffic → Junction Network. The selected edge opens its assignment in the existing inspector.
- The inspector lists the four edges and lets an operator assign one existing crosswalk (defined in Traffic → Crosswalks) to each edge, or clear the assignment. Linked edges are visually distinguished.
- Persist `crosswalk_edges` in the existing `config/intersections.json` network document using schema version 1. Older configurations without the optional mapping load with all four edges null.
- Backend rejects unknown edge keys, malformed crosswalk IDs, and assigning the same crosswalk to multiple junction edges. Removed crosswalks retain their ID and show a missing-reference warning for manual correction.
- Crosswalk data remains owned by the original crosswalk service. No duplicate stores, new routes, traffic controller, crosswalk detection, or signal authority.

## Verification

Focused network persistence and validation tests; Junction Network UI static wiring; structure/version checks; frontend typecheck/build and Windows full-runner smoke. Owner validates clicking all four edge labels, assigning distinct crosswalks, saving/reloading, deletion handling and node dragging before PASS.
