# Start Here — V0321

V0321 / `0_3_21` corrects the Crosswalks diagram. Previous candidate: `0_3_20` (unaccepted). Owner-confirmed passed baseline: `0_3_11`.

## Change

In Traffic → Crosswalks, the seven white zebra stripes now run **horizontally** across a **vertical** pedestrian crossing connecting Side A (top) and Side B (bottom). Camera A and camera B remain opposite each other, and all crosswalk editing, assignments and persistence behavior remain unchanged. This remains configuration-only, not dual-camera inference or live traffic control.

## Update and test

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Full validation and owner PASS remain necessary. `0_3_11` is still the accepted baseline.
