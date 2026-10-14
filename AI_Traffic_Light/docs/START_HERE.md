# Start Here — V0327

Current candidate `0_3_27` (previous `0_3_26`); owner-confirmed passed baseline `0_3_11`.

V0327 repairs a V0326 startup regression assertion for the new simulation/ESP preview branches. Runtime behavior remains the same: numbered 1–4 topology endpoints and simulation cameras via Camera Settings → New camera → Simulation camera → Save.

## Assign crosswalks to junction edges

1. Define your crossings under **Traffic → Crosswalks**.
2. Open **Traffic → Junction Network** and select a junction. Click any **1, 2, 3, 4** label directly on the junction card.
3. Under **Crosswalks by edge** in the inspector, choose a saved crosswalk for the selected side (or **No crosswalk** to clear it). Repeat for the other sides.
4. Click **Save network**. Refreshing or restarting preserves edge assignments. Deleted crosswalks show a missing ID until explicitly corrected.

The numbered labels identify junction connection points regardless of orientation; connections are configuration-only and do not issue signal commands.

## Update and test

```powershell
cd D:\AiTL
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Validate UI and full runner before PASS; accepted baseline remains `0_3_11`.
