# Patch 0_5_38 — Restore complete release documentation

Candidate `0_5_38`, previous `0_5_37`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Restore the full changelog and local-testing guide after the `0_5_37` GitHub write truncated their contents. Retain all historical entries, current candidate notes, the mirrored 3D signal-post fix and its regression. No application runtime behavior changes.

Validation: confirm both documents retain their historical sections, run `python scripts/check_structure.py`, frontend typecheck/build and the normal Windows owner runner `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. Owner PASS remains required; accepted baseline remains `0_5_0`.
