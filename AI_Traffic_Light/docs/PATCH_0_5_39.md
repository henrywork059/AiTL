# Patch 0_5_39 — Shared 3D mirror utility keyboard regression

Candidate `0_5_39`, previous `0_5_38`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The V0537 camera signal-post fix moved the canonical `simulationSourcePoint` transform into `apps/pc-studio/frontend/src/components/simulation3dMotion.ts`, and the scene imports and uses it. The V0523 keyboard test still demanded an inline `sourcePoint` declaration inside `SimulationCamera3D.tsx`. As a result, the Windows runner and feature-branch GitHub Actions both fail even though the keyboard handler, focus, editor guard and shared projection remain present.

Replace the obsolete source-text assertion with checks that `simulationSourcePoint` is exported and wired into the component. Retain all other keyboard/editor regression coverage and the V0515 behavior-level mirror tests. No runtime code, traffic safety, camera API or ESP hardware changes.

Validation: `python scripts/test_v0523_3d_keyboard.py`, `python scripts/test_v0515_3d_simulation.py`, structure, all offline regressions, frontend TypeScript typecheck/build, then Windows owner test `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. CI success is not owner PASS.
