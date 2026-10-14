# Patch 0_4_2 — Crosswalk test alignment

Previous candidate: `0_4_1`. Owner-confirmed stable baseline: `0_4_0`.

Fixes the Crosswalk static regression that still required the deleted single-camera preview text after V0401. Checks now cover the two simulated sources, pair assignment and numbered edge labels. There are no runtime changes.

Windows validation is still pending. Run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests` from the project root.
