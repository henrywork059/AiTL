# Patch 0_4_22 — Responsive text/panels and clear selected-region borders

**Candidate:** `0_4_22`. **Previous candidate:** `0_4_21`. **Accepted stable baseline:** `0_4_14`.

## Changes

- Shared `styles/base.css`: fluid heading text sizes and safe line wrapping for visible labels, buttons and content.
- Shared `styles/layout.css`: flexible page headers, shrinkable page-grid children and non-clipping page containers.
- Shared `styles/components.css`: shrinkable panels, wrapping panel headers/status pills/camera statuses, fluid metric text and expanding status bar.
- Page-specific CSS: remove single-line truncation in Junction Network camera/link names and Signal Control scenario descriptions; allow Simulation Experiment tab/scenario/rule text to wrap and enable document scrolling on low-height screens. Preserve scrollable wide data tables and camera aspect ratios.
- Both normal and selected region polygons remain fully transparent. Selected regions use fully opaque pale-yellow `#FFF5C7` 6px (Crosswalks) / 7px (legacy) dashed outlines and the original vertex controls. No glow or fill.
- Update V0417/V0418/V0420 historical tests; add `test_v0422_responsive_layout.py`. Preserve both V0421 simulation-camera pairs, camera/API selection, geometry, storage and signal decisions.

## Validation

The source-level rules and previous test expectations can be inspected remotely. Windows Python regressions, frontend TypeScript/build, backend live smoke, and actual responsive UI inspection remain required before owner PASS. V0422 is a candidate.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
