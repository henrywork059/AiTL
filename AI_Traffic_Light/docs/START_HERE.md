# Start Here — V0320

V0320 / `0_3_20` is the Crosswalk configuration candidate. Previous candidate: `0_3_19` (unaccepted). Passed baseline: `0_3_11`.

## New Crosswalks page

Open **Traffic → Crosswalks** to add, name, edit and remove crosswalks. Set camera Side A and Side B from your saved ESP camera profiles on opposite pedestrian approaches, as illustrated by the crosswalk diagram. Save definitions to `config/crosswalks.json`; the page displays saved camera connection status. No simultaneous two-camera inference or signal control is enabled.

## Update and test

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Owner PASS and full Windows test are required. `0_3_11` remains baseline.
