# Start Here — V0324

Current candidate `0_3_24` (previous `0_3_23`); owner-confirmed passed baseline `0_3_11`.

## Assign crosswalks to junction edges

1. Define your crossings under **Traffic → Crosswalks**.
2. Open **Traffic → Junction Network** and select a junction. Click any **N, E, S, W** label directly on the junction card.
3. Under **Crosswalks by edge** in the inspector, choose a saved crosswalk for the selected side (or **No crosswalk** to clear it). Repeat for the other sides.
4. Click **Save network**. Refreshing or restarting preserves edge assignments. Deleted crosswalks show a missing ID until explicitly corrected.

The labels describe cardinal junction edges; connections are configuration-only and do not issue signal commands.

## Update and test

```powershell
cd D:\AiTL
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Validate UI and full runner before PASS; accepted baseline remains `0_3_11`.
