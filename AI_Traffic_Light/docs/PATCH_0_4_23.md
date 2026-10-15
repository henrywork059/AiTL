# Patch 0_4_23 — Translucent Region Editor polygons

**Candidate:** `0_4_23`. **Previous candidate:** `0_4_22`. **Accepted stable baseline:** `0_4_14`.

## Corrected behavior

- Crosswalk Region Editor normal polygons use `rgba(87, 255, 237, 0.10)` and selected polygons use `rgba(255, 246, 210, 0.22)`; both display the camera frame beneath the tint.
- Selected polygon retains a fully opaque `#FFF5C7` 6px dashed border and draggable numbered vertices. Removed SVG's redundant `fill="none"` so the CSS fills are the only fill contract.
- Hidden legacy editor uses the same translucent fills and existing 7px selected border. Live AI/simulation region overlays stay clear.
- Updated V0417/V0418/V0420/V0422 regressions to reject a reversion to fully unfilled editor polygons and verify both alpha values stay below 0.30.
- No change to region geometry, camera pairing, Side A/B, data/API schemas, simulation images, saved settings or signal safety.

## Verification / owner acceptance

Focused CSS/JSX contract validation is possible in the connected source. Windows Python regressions, frontend TypeScript/build, actual camera-frame appearance, startup and backend live smoke remain required; do not mark PASS automatically.

From repository root:

```powershell
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Inspect Crosswalks → Edit regions in a running simulation; verify normal and selected tint, camera visibility, dashed border, vertex dragging and save/reload. The passed baseline remains `0_4_14` until owner confirmation.
