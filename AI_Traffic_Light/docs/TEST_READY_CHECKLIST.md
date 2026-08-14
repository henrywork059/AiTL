# Test-Ready Checklist — 0_1_1

Use this checklist when testing the project after uploading the patch.

## Backend

- [ ] Backend starts with `scripts\start_pc_studio_backend_windows.bat`.
- [ ] `http://127.0.0.1:8000/docs` opens.
- [ ] `http://127.0.0.1:8000/health` returns `ok: true`.
- [ ] `http://127.0.0.1:8000/api/smoke/status` returns version `0_1_1`.
- [ ] Camera Sources can start/stop simulation and display moving frames.
- [ ] `scripts\test_backend_smoke_windows.bat` shows all `PASS`.

## Frontend

- [ ] Frontend starts with `scripts\start_pc_studio_frontend_windows.bat`.
- [ ] `http://localhost:5173` opens.
- [ ] Dashboard loads.
- [ ] Sidebar navigation works.
- [ ] Live AI page shows mock road/crossing scene.
- [ ] Zones are visible.
- [ ] Mock boxes are visible.
- [ ] Confidence slider changes visible detection count.
- [ ] Logs page shows mock logs.
- [ ] Settings page shows API base and backend version.

## Safety

- [ ] App clearly says real traffic control is disabled.
- [ ] App clearly says real AI/camera/training are not implemented.
- [ ] No code attempts to control real public traffic infrastructure.

## Pass criteria

0_1_1 passes if:

```text
frontend starts
backend starts
mock API connects
mock GUI renders
smoke test endpoints pass
```

0_1_1 does not need real AI or completed ESP32/Raspberry Pi firmware.
