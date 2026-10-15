# Start Here — V055

Current candidate `0_5_5`, previous candidate `0_5_4`, owner-accepted baseline `0_5_0`.

V055 updates two stale offline regressions (Camera Settings structure and historical V0418 Region Editor side-switch behavior) to reflect existing implemented code. No application runtime code or camera/region data is changed. Use the existing Windows runner to validate all regressions, frontend build and smoke before acceptance.

## Previous V054

Candidate `0_5_4`, previous `0_5_3`, accepted baseline `0_5_0`. The Region Editor creates distinct Side A/B regions and supports an editable backend ID; Save regions persists them. Per-class detection counts are exposed for the active camera only.

## Previous V053

Current candidate `0_5_3`, previous candidate `0_5_2`, accepted baseline `0_5_0`.

V053 repairs V052 release metadata so the update runner can proceed. The Region Editor Save regions button introduced in V052 is unchanged. Toggle the top-left AI Traffic Light panel to show or hide simulation options; default is hidden. The toggle does not stop existing simulation or modify saved assignments.

## Previous V0501 candidate

Current candidate `0_5_1`, accepted baseline `0_5_0`.

## Previous stable release


Current stable release `0_5_0` (previous `0_4_24`); owner-accepted stable baseline `0_5_0`.

The owner confirmed PASS for V0424 and requested the next stable version. V050 is a release-label/documentation promotion of that accepted implementation, with no app, backend, hardware, signal, API or data changes.

V0424 combines each Crosswalk Side A/B camera selector and connection state into one section per side, arranged as two columns above the schematic (stacked on narrow screens). The duplicate status rows and bottom Side B picker are removed. Camera assignment, simulation, regions and V0423 translucent fills are unchanged.

V0423 restores light translucent mint fills (10%) to ordinary Crosswalk regions and pale cream fills (22%) to selected regions, retaining their bright dashed outlines, draggable vertices and visible camera feed; legacy editor matches. Live AI/simulation overlays remain clear. V0422 standardized responsive panel/text alignment and used fully clear selected region interiors with bright outlines. V0421 adds a second selectable saved simulation camera pair (C/D) while retaining Pair 1 (A/B). V0420's pale selected-region fill was superseded by V0422's fully transparent interior and emphasized border. V0419 fixes a duplicate-selector regression test assumption without changing runtime code. V0418 adds clickable Saved cameras, Side A/B toggle buttons, an unannotated cars-and-people simulation, centered status pills, and a pre-patch code archive. V0417 makes region polygon interiors fully transparent while keeping outlines and edit handles. V0416 removes the unused Traffic Zones page and uses Regions terminology throughout the interface while preserving storage/API names. V0415 slightly darkens the dark-mode canvas to #444557 while preserving the accepted sidebar and panel palette. V0414 removes obsolete sidebar assumptions from the historical V0409 regression; V0413 retains the sidebar visual contract. V0413 gives the sidebar quiet slate selection, muted section labels and thin dividers; mint remains reserved for functional emphasis. V0412 corrects a false Junction card layout test assertion by selecting the latest matching CSS rule instead of an earlier grouped rule; V0411's actual UI is unchanged. V0411 restructures Junction Network cards into a separate title bar and centered data with labels 1–4 on the four sides, plus fluid text. V0410 fixes two Camera Settings TypeScript type errors with no behavior or theme change. V0409 applies the slate/mint palette, boxed sidebar headings and inside-card junction edge labels. V0408 verifies the system-Python Uvicorn child directly under AiTL's virtualenv parent (as observed in the Windows process trace). V0407 improved recognition of the Windows Uvicorn reload worker that can own port 8000 during an update. V0406 fixes two stale Junction Network test assertions without changing runtime UI behavior. V0405 adopts the #57FFED dark theme and selected-state indicators. V0404 fixes the outdated structure check blocking the V0403 startup tests; the new palette remains unchanged. V0403 refines shared UI styles without changing the current camera, crossing or junction logic. V0402 fixed a stale Crosswalk regression assertion; functionality from V0401 is unchanged. Camera Settings saves two mirrored simulated cameras. Crosswalks displays numbered edges and can assign the pair to Side A and B. Junction edge labels no longer cover node content, and dragging retains its initial pointer offset. Camera Sources and the old Zone Editor are hidden legacy routes; Traffic → Zones is reserved and intentionally empty.

## Assign crosswalks to junction edges

1. Define your crossings under **Traffic → Crosswalks**.
2. Open **Traffic → Junction Network** and select a junction. Click any **1, 2, 3, 4** label directly on the junction card.
3. Under **Crosswalks by edge** in the inspector, choose a saved crosswalk for the selected side (or **No crosswalk** to clear it). Repeat for the other sides.
4. Click **Save network**. Refreshing or restarting preserves edge assignments. Deleted crosswalks show a missing ID until explicitly corrected.

The numbered labels identify junction connection points regardless of orientation; connections are configuration-only and do not issue signal commands.

## Update and test

```powershell
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Validate UI and full runner before PASS; accepted baseline remains `0_5_0`.
