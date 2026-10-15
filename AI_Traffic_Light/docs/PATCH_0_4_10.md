# Patch 0_4_10 — Camera Settings TypeScript guard correction

**Candidate:** `0_4_10`. **Previous candidate:** `0_4_9`. **Owner-accepted baseline:** `0_4_0`.

## Failure

The V0409 Windows update completed offline regressions but `tsc --noEmit` stopped on two TS2367 errors in `CameraSourcesPage.tsx` near its Save and Connect buttons. Both compared `newCameraType === "simulation"` within a JSX branch already restricted to `newCameraType === "esp32"`.

## Minimal patch

Remove only those redundant unreachable type checks. Save and Connect retain busy, selected-streaming, and required host/source-ID validations. The separate simulation-pair workflow and all V0409 styles remain unchanged.

Extend `test_camera_settings_page_structure.py` to assert the ESP-only branch does not re-check for simulation. Windows TypeScript compilation, frontend production build, smoke, and visual acceptance remain to be confirmed by the owner.

Update/test/start command from repository root:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
