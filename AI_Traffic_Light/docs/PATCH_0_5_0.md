# Stable Release 0_5_0 — Owner acceptance of V0424

**Stable version:** `0_5_0`. **Previous version:** `0_4_24`. **Passed baseline:** `0_5_0`.

## Owner acceptance and release meaning

- The owner explicitly confirmed PASS for V0424 and requested the next stable version. V050 promotes the accepted implementation without adding untested functionality.
- This milestone changes only version/release metadata and guidance; the tested Crosswalk camera-side layout, region translucency, camera assignment/simulation pairs, persistence, and signal-safety rules remain intact.
- The version label changes from `0_4_24 Candidate` to `0_5_0 Stable`. The backend and frontend derive the current version from the existing release surfaces.
- Historical patch records are retained unchanged. No new ESP firmware, APIs, datasets, runtime settings or application dependencies.

## Verification

- Check root `VERSION`, the frontend version mirror, this release document, the changelog and current docs for consistent `0_5_0` / `0_4_24` / `0_5_0` release-state fields.
- Normal Windows startup/update/regressions and physical-device checks were not rerun for this metadata-only release. Owner's PASS applies to the preceding accepted implementation.

To refresh local files and confirm the stable version label, run from the repository root:

```powershell
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```
