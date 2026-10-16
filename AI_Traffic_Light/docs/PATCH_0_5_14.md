# Patch 0_5_14 — Release consistency after Camera AI Preview typecheck fix

**Candidate:** `0_5_14` | **Previous:** `0_5_13` | **Accepted baseline:** `0_5_0`

## Scope

- Complete the release bundle missed by candidate `0_5_13`: the current patch document, changelog, Start Here, Local Testing, Test Ready Checklist, and frontend `PROJECT_VERSION` constant.
- Retain the small fix in `CameraDetectionView.tsx` from `0_5_13`: null-safe `cameraStatus?.resolution?.width` and `cameraStatus?.resolution?.height` fallbacks. No additional runtime code, inference, API, hardware, signal timing, or actuation changes.
- Fix the structure/version validation gate that blocked the owner’s update/start workflow for `0_5_13`. Preserve earlier release history and baseline `0_5_0`.

## Validation

- Static release contract: `scripts/check_structure.py` must recognize `docs/PATCH_0_5_14.md`, matching current-candidate documentation, `CHANGELOG.md`, and frontend `projectVersion.ts` containing only `0_5_14`.
- From `D:\AiTL`, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

- Verify the release/structure check, frontend TypeScript check, Vite build, backend startup and `/health`; inspect Camera AI Preview with and without an available camera. Preserve independent Crosswalk/Network virtual-only signal behavior.
- Full Windows tests, real-camera testing, and owner PASS remain pending. This is **not** an accepted stable release.
