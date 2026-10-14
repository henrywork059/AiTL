# V0325 Test-Ready Checklist

```text
version: 0_3_25
previous_version: 0_3_24
passed_baseline: 0_3_11
status: Startup regression assertion fix candidate
```

- [ ] Camera Settings and Crosswalks page regressions pass without relying on adjacent entries in `CAMERA_POLL_PAGES`.
- [ ] Windows update/test/run completes, frontend opens and backend health/live smoke pass.
- [ ] V0324 junction-edge acceptance checks below still pass.


- [ ] All junction cards show clickable N/E/S/W edge labels, linked/selected styling and tooltips.
- [ ] Selecting an edge opens its crossing assignment in Junction Network inspector.
- [ ] The dropdown lists saved crosswalks, shows missing references and supports No crosswalk.
- [ ] One crossing cannot occupy more than one edge; backend rejects duplicate or malformed IDs.
- [ ] Older network JSON without `crosswalk_edges` loads as four empty edges; save/restart preserves mappings.
- [ ] Existing junction camera, simulation, drag, topology and traffic state behaviors remain unchanged.
- [ ] `python scripts/test_intersection_network.py` passes.
- [ ] `python scripts/test_junction_network_frontend_structure.py` passes.
- [ ] `python scripts/check_structure.py`, frontend typecheck/build and full Windows runner pass.
- [ ] Owner confirms PASS, otherwise `0_3_11` remains accepted baseline.
