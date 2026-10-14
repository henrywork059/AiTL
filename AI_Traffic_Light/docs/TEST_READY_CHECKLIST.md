# V0327 Test-Ready Checklist

```text
version: 0_3_27
previous_version: 0_3_26
passed_baseline: 0_3_11
status: Camera Settings preview regression assertion repair candidate
```

- [ ] Camera Settings regression asserts both selected simulation and physical ESP preview isolation and passes.
- [ ] Windows changed-tests startup completes all selected regressions, frontend checks, backend health and live smoke.
- [ ] New Camera supports selecting and saving one simulation camera without IP; its preview and Crosswalk assignment work after restart.
- [ ] Junctions show 1–4 edge labels with no N/E/S/W visible; topology links persist selected endpoint numbers.
- [ ] Existing crosswalk-to-edge mappings and physical ESP stream controls remain intact.
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
