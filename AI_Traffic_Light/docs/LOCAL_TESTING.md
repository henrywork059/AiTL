# Local Testing — V0319

Expected release state:

```text
version: 0_3_19
previous_version: 0_3_18
passed_baseline: 0_3_11
status: Collapsible camera settings and status candidate
```

## Focused checks

1. Run `python scripts/test_camera_settings_page_structure.py`, `python scripts/test_frontend_polling_structure.py`, and `python scripts/check_structure.py` from `AI_Traffic_Light`.
2. From `apps/pc-studio/frontend`, run `npm run typecheck` and `npm run build`.
3. Open Camera Settings: saved cameras should appear in a status strip with semantic colors and a clear selected preview; status should refresh without changing dropdown selection or unsaved input.
4. Add two IP profiles using the collapsible manager; select each via the always-visible dropdown, connect/start/stop and check streaming/connected/reconnecting/error colors and counters.
5. Expand/collapse camera settings and diagnostics; verify advanced OV2640 controls, saved settings, start/stop actions and error messages remain usable.
6. Activate simulation in Camera Sources: physical-camera strip should show paused stream states, and the Settings preview should not show simulation as physical input. Switch back and confirm restored status.
7. Check offline IP, deletion of active camera, and other background streams remaining active.

## Owner validation

```powershell
& "W:\\Code Project\\AiTL Ptoject\\AiTL\\AI_Traffic_Light\\scripts\\update_test_run.ps1"
```

Full Windows tests/live smoke and a real ESP remain required for owner PASS. `0_3_11` remains the accepted baseline.
