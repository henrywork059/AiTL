# Patch 0_5_33 — Correct Hallmark shell regression expectation

Candidate `0_5_33`, previous `0_5_32`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

The V0532 UI patch passed Python compilation and repository structure validation. Its new source-wiring regression then failed because it expected an unconditional redirect from Simulation Experiments. The existing `toggleSimulationTools` intentionally redirects only when `showSimulationTools` is true and the active page is `simulation_lab`. A toggle that opens the tools must not redirect.

Correct that one assertion in `scripts/test_v0532_hallmark_shell.py`. Do not change application runtime, navigation handlers, styling, APIs, simulation behavior or physical outputs. Keep the V0532 labeled native button and removal of redundant sidebar labels.

**Verify:** `python scripts/test_v0532_hallmark_shell.py`, full offline candidate CI, structure, frontend TypeScript typecheck/build. Windows owner test remains required: pull the feature branch, run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` from repository root, verify click/keyboard open-close and conditional dashboard return, light/dark and narrow layout. Explicit PASS pending.
