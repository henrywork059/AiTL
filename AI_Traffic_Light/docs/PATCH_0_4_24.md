# Patch 0_4_24 — Crosswalk camera-side layout

**Candidate:** `0_4_24`. **Previous candidate:** `0_4_23`. **Accepted baseline:** `0_4_14`.

## Scope

- Move existing Crosswalk Side A and Side B selectors into an equal-width left/right grid above the unchanged schematic.
- Display each camera state in the same labeled section as its picker. Use concise `Side A` / `Side B` labels rather than repeating descriptions.
- Remove the duplicated side-status rows below the drawing and the bottom Side B selector; at widths below 720px stack the two sections.
- Extend the existing Crosswalk structural regression to verify one picker per side, order, status ownership and CSS responsive rules.
- No backend, API, persistence, schema, camera pair, stream, region overlay, signal or drawing changes.

## Verification

- Source-level structural assertions check that the two selectors are unique and above the schematic, state uses the existing `cameraState` helper, and CSS provides two columns with responsive stacking.
- Run Windows full changed-tests updater, frontend TypeScript/build, backend smoke and visually verify both camera selections, state labels, missing camera warnings and responsive layout before PASS.
- Owner accepted baseline remains `0_4_14`.

```powershell
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```
