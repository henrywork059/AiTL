# Patch 0_4_17 — Transparent region polygons

Candidate `0_4_17`; previous candidate `0_4_16`; accepted baseline `0_4_14`.

## Scope

- Crosswalk Region Editor: normal and selected quadrilateral polygon interiors now use `fill: none`; mint outlines remain on unselected regions. Selected regions use a thicker, contrasting warning-colored dashed outline with numbered drag handles while retaining fully transparent interiors.
- Live AI, simulation/mock and hidden legacy Region Editor: polygon interiors now use `fill: none`; their existing strokes and labels remain.
- Dataset Review object-label boxes still use their existing box fill; the shared `--color-zone-fill` token is **not modified** to avoid coupling unrelated visual elements.
- Add focused `test_v0417_region_transparency.py` to protect appearance and interaction/compatibility invariants.

No JavaScript/TypeScript behavior, geometry, camera transport, persistence, APIs, signal logic or dependencies changed beyond the version label.

## Windows validation

Run the standard update, test and start script. Confirm translucent-looking interiors are in fact fully transparent: the camera image should be visible at 100% opacity within each region. Inspect both unselected and selected regions, and drag all four numbered vertices. Validate Live AI overlays and unchanged Dataset Review bounding boxes. Windows typecheck, smoke and owner PASS pending.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
