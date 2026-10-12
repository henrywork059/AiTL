# Local Testing — V0321

```text
version: 0_3_21
previous_version: 0_3_20
passed_baseline: 0_3_11
status: Crosswalk schematic orientation correction candidate
```

## Focused checks

1. Run `python scripts/test_crosswalks_frontend_structure.py` and `python scripts/check_structure.py` from `AI_Traffic_Light`.
2. Run `npm run typecheck` and `npm run build` in `apps/pc-studio/frontend`.
3. Inspect Traffic → Crosswalks: zebra stripes run left-to-right (horizontal), and the walking corridor, path guides and arrows connect Side A at the top to Side B at the bottom.
4. Switch crosswalks and assign cameras on both sides to confirm existing editing and diagram highlighting remain unchanged.

## Owner validation

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Windows GUI validation and owner PASS are pending; `0_3_11` remains the passed baseline.
