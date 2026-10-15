# Patch 0_4_6 — Junction Network regression assertion alignment

Previous candidate: `0_4_5`. Stable owner-accepted baseline: `0_4_0`.

The V0405 Windows startup stopped at `test_junction_network_frontend_structure.py` because its historical assertion required `Simulation · 1 shared camera`. A second assertion in the same file required the removed description `single selected AI source`. The Junction Network page now shows `Simulation active` / `Physical cameras` and retains an editable `primary_source_id` control.

Both outdated assertions are replaced with checks of those active interface elements. No runtime files are modified beyond the frontend version label.

Run the existing one-line updater, tests and app launcher from the repository root:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```

Owner PASS pending; stable baseline stays `0_4_0`.
