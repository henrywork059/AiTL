# Patch 0_4_14 — Remove stale V0409 navigation assertions

**Candidate:** `0_4_14`. **Previous candidate:** `0_4_13`. **Accepted stable baseline:** `0_4_0`.

## Failure

The user's V0413 first run completed the update runner checks and two earlier visual regressions before stopping at `test_v0409_palette_layout.py`: the historical V0409 test required `color-nav-heading-surface`. V0413 intentionally removed that token when replacing mint-boxed navigation headings with muted labels and thin dividers.

## Minimal repair and prevention

Remove old sidebar-specific color/style assertions from the V0409 palette test, keeping its core palette and Junction Network layout coverage. The newer `test_v0413_quiet_navigation.py` remains the single owner of sidebar appearance and its light/dark text contrast. This avoids duplicate contradictory test contracts after a redesign.

No runtime code or CSS changes.

## Validation status

Source-level checks were inspected. The complete Python test suite, frontend TypeScript/build, Windows restart, and backend live smoke could not be executed in this environment. They remain **unverified** until the local updater completes them. Do not treat source-level checks as integrated PASS.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
