# Patch 0_4_20 — Pale translucent selection for region polygons

Candidate `0_4_20`. Previous candidate `0_4_19`. Owner-accepted stable baseline `0_4_14`.

## Design change

Unselected region polygons retain `fill: none`. Selected region polygons now use `fill: rgba(255, 246, 210, 0.22)`, a light 22%-opaque cream that allows the camera feed to remain visible. The existing contrasting thicker dashed yellow outline and draggable numbered vertices remain.

The Crosswalk Region Editor's SVG no longer sets an unconditional `fillOpacity={0}` which prevented the selected CSS highlight from rendering. `fill="none"` remains as a baseline SVG presentation attribute, overridden by the more specific selected CSS rule. The hidden legacy region editor uses the same selected fill. Live AI region overlays, simulated-region outlines and Dataset Review bounding boxes remain unchanged.

The existing complete pre-V0418 backup stays at `docs/backups/V0417_PRE_V0418_CODE.md`; AGENTS guidance is updated with this new selection contract.

## Regression and test

The V0417/V0418 structure tests are aligned with the new requested selection appearance, and `test_v0420_selected_region_highlight.py` checks the opacity range and both editor states.

Runtime UI behavior, TypeScript/build and live backend smoke require Windows verification. No camera data, saved region geometry, APIs, signal-policy logic or dependencies changed.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
