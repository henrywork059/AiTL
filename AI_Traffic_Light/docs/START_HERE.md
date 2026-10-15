# Start Here — V0405

Current candidate `0_4_5` (previous `0_4_4`); passed stable baseline `0_4_0`.

V0405 adopts the #57FFED dark theme and selected-state indicators. V0404 fixes the outdated structure check blocking the V0403 startup tests; the new palette remains unchanged. V0403 refines shared UI styles without changing the current camera, crossing or junction logic. V0402 fixed a stale Crosswalk regression assertion; functionality from V0401 is unchanged. Camera Settings saves two mirrored simulated cameras. Crosswalks displays numbered edges and can assign the pair to Side A and B. Junction edge labels no longer cover node content, and dragging retains its initial pointer offset. Camera Sources and the old Zone Editor are hidden legacy routes; Traffic → Zones is reserved and intentionally empty.

## Assign crosswalks to junction edges

1. Define your crossings under **Traffic → Crosswalks**.
2. Open **Traffic → Junction Network** and select a junction. Click any **1, 2, 3, 4** label directly on the junction card.
3. Under **Crosswalks by edge** in the inspector, choose a saved crosswalk for the selected side (or **No crosswalk** to clear it). Repeat for the other sides.
4. Click **Save network**. Refreshing or restarting preserves edge assignments. Deleted crosswalks show a missing ID until explicitly corrected.

The numbered labels identify junction connection points regardless of orientation; connections are configuration-only and do not issue signal commands.

## Update and test

```powershell
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Validate UI and full runner before PASS; accepted baseline remains `0_4_0`.
