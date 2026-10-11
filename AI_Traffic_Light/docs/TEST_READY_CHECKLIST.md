# V0318 Test-Ready Checklist

```text
version: 0_3_18
previous_version: 0_3_17
passed_baseline: 0_3_11
status: Camera Settings page candidate
```

## Camera Settings

- [ ] Operate sidebar has a distinct Camera Settings page; Camera Sources still supports simulation.
- [ ] Add multiple ESP camera IPs and source IDs, select each saved camera from the dropdown, and restore its settings.
- [ ] Preview displays the selected live ESP feed only; switching, simulation, stopping and deleting do not show another camera's stale frame.
- [ ] Live status displays selected source/IP, connection, measured FPS, frame age and detailed device/transport telemetry.
- [ ] Resolution, JPEG quality, FPS, basic and advanced OV2640 settings persist and apply when the stream is started; editing a running stream remains locked.
- [ ] Offline/reconnecting cameras show accurate state and errors; other ESP streams survive switching.

## Validation and acceptance

- [ ] `python scripts/check_structure.py` passes.
- [ ] `python scripts/test_camera_settings_page_structure.py` passes.
- [ ] `python scripts/test_frontend_polling_structure.py` passes.
- [ ] Frontend `npm run typecheck` and `npm run build` pass.
- [ ] Full Windows `update_test_run.ps1` and physical ESP connection test pass.
- [ ] Owner confirms PASS. Until then `0_3_11` remains the passed baseline.
