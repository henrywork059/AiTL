# Start Here — V0323

Current candidate: `0_3_23` (previous candidate `0_3_22`, accepted baseline `0_3_11`).

## What's new

- Open Traffic → Crosswalks. Add/select a crosswalk, then **Edit regions** to enter a dedicated wide editor. Add/edit/delete a quadrilateral, dragging its four numbered corners over the chosen camera or simulated image. **Back to crosswalks → Save changes** persists the shared region definitions.
- Side A and Side B use the *same* saved region coordinates; they are not geometrically calibrated to different viewpoints.
- Start/stop shared simulation from either Crosswalks or Junction Network. There is only one simulated camera; the existing camera service handles physical-camera pause/resume.

## Pull, test, run

```powershell
cd D:\AiTL
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Run the full Windows runner and verify physical camera preview before owner acceptance. The accepted baseline remains `0_3_11`.
