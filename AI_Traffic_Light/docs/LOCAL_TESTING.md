# Local Testing — V0318

Expected release state:

```text
version: 0_3_18
previous_version: 0_3_17
passed_baseline: 0_3_11
status: Camera Settings page candidate
```

## Focused checks

1. Run `python scripts/check_structure.py` and `python scripts/test_camera_settings_page_structure.py` from `AI_Traffic_Light`.
2. Run `python scripts/test_frontend_polling_structure.py`, frontend `npm run typecheck` and `npm run build`.
3. Confirm the new Operate → Camera Settings page renders preview, saved camera dropdown, IP entry, camera controls, stream controls and live selected-source telemetry.
4. Save two IP camera profiles, switch between them, check that the dropdown selects the current preview source, and verify settings reload after navigation/restart.
5. Start/stop an ESP stream, verify selected-only preview and real measured FPS/status. Activate simulation in Camera Sources, confirm Camera Settings does not mislabel simulated frames as ESP live feed, and restore the physical source.
6. Check invalid/offline IP error handling, delete a selected camera, and verify other streams remain unaffected.

## Full owner validation

```powershell
& "W:\\Code Project\\AiTL Ptoject\\AiTL\\AI_Traffic_Light\\scripts\\update_test_run.ps1"
```

The Windows owner runner performs complete tests, typecheck/build, smoke and launch. A real ESP/OV2640 and LAN are required for actual streaming confirmation. The shared AI pipeline still processes one selected camera at a time. `0_3_11` remains the passed baseline until owner PASS.
