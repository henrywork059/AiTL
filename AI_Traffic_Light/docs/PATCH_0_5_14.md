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

## Follow-up in the same 0_5_14 candidate — coordinated Crosswalk Network

- Keep the previously completed per-crosswalk Side A/B camera-to-controller routing, with fresh class counts and region averages. No duplicate inference or camera registry.
- Each saved Network link optionally holds `movement_conflicts`, a validated subset of four ordered pairs: vehicle↔vehicle, source vehicle→destination pedestrian, source pedestrian→destination vehicle, and pedestrian↔pedestrian. Empty/missing means independent legacy behaviour; user must explicitly configure physical conflicts.
- New pure `crosswalk_signal_coordinator` interlock operates **only on published software simulation/virtual previews**. It grants nonconflicting movements, pauses a blocked crosswalk's local phase clock and displays virtual all-red hold. When a conflicting grant ends, the next competing movement waits at least two further simulation seconds before permission. Existing local protected yellow, pedestrian WALK/CLEAR and all-red timing remains unchanged.
- Emergency requests on configured directional links now require explicit movement conflicts and remain bounded by local phase/cycle limits; a request held too long expires and its pending permission is cancelled. Physical signal actuation is still not implemented.
- Network editing exposes conflict-pair checkboxes per connected link and displays signal hold/priority reasons and active countdowns. `GET /api/traffic/crosswalk-signals` adds `coordination_status`, `coordination_reason`, `coordination_wait_seconds` and virtual signal-level hold/blocked-by detail. Existing response envelope and request IDs remain unchanged.
- Focused simulation regression: `scripts/test_v0514_network_conflicts.py` covers conflict combinations, no simultaneous conflicting published greens, bounded clearance, paused local clocks, opt-in emergency priority and legacy unconfigured links.
- This is an educational **virtual coordination interlock**, not certified conflict control. Applying topology changes during an active cycle can cause an immediate virtual red clamp; physical signal outputs are unavailable. Never infer movement conflicts from adjacency. Full owner acceptance pending.
