# Patch 0_4_19 — Correct V0418 CSS selector test

Candidate `0_4_19` · Previous candidate `0_4_18` · Owner-accepted stable baseline `0_4_14`.

## Reported Windows failure

The updater's 19 selected backend regressions reached `test_v0418_camera_region_ui.py`, which stopped at `assert "cursor: pointer;" in entry`. Actual `styles/components.css` sets `cursor: pointer` in the first `.camera-status-entry` block. A later block sets `background: var(--color-surface-raised)`. The V0418 test helper mistakenly returned only the last block.

## Minimal repair

- Have the existing test's `css_rule` helper join declarations across repeated exact selector rules.
- Add a deterministic two-block CSS sample verifying both early cursor and later background declarations can be checked.
- Retain all V0418 application changes and the complete source recovery document `docs/backups/V0417_PRE_V0418_CODE.md` unchanged.
- Add an agent-guideline reminder not to make single-block assumptions for CSS selectors.

No runtime CSS, JSX, camera rendering, traffic-signal logic, region data or API changes. Local Windows Python, frontend typecheck/build, startup and live smoke are still acceptance gates.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
