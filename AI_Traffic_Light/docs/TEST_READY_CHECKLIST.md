# V0408 Test Checklist

```text
version: 0_4_8
previous_version: 0_4_7
passed_baseline: 0_4_0
status: Windows system-Python Uvicorn child recognition candidate
```

- [ ] Mocked Windows PowerShell worker/parent identity regression passes.
- [ ] System-Python Uvicorn child on port 8000 restarts through verified AiTL parent.
- [ ] Application startup and backend health/live smoke pass; unrelated processes remain untouched.
- [ ] Windows runner safely restarts project Uvicorn reload parent/worker on port 8000, without closing unrelated processes.
- [ ] Other Python services on port 8000 remain protected.
- [ ] Backend health, frontend launch and smoke pass.
- [ ] Junction Network regression asserts current mode text and primary-camera selector, not removed copy.
- [ ] Windows update/test/run continues past the prior Junction Network failure.
- [ ] Dark mode displays `#57FFED` accent; light mode uses accessible dark teal.
- [ ] Selected navigation, tabs, mode buttons, Crosswalks and Dataset rows show dots/bars/rings as applicable.
- [ ] Live AI checked filters and Junction edge selection have visible active styling.
- [ ] Keyboard focus, button hover, app startup and existing camera/junction behavior remain correct.
- [ ] Updated structure validator accepts the new semantic dark base token and rejects an invalid token.
- [ ] V0404 changed-tests startup proceeds beyond the previous structure failure.
- [ ] Shared semantic palette passes contrast validation; light/dark page styles share tokens.
- [ ] Buttons, input fields, panels, navigation selection and analytics/simulation tabs are usable.
- [ ] Simulation tabs support keyboard navigation; chart labels remain readable.
- [ ] Windows build and live smoke pass; prior functionality unchanged.
- [ ] Crosswalk static regression passes with mirrored-pair assertions.
- [ ] Both simulation profiles are saved and are vertically mirrored views of the same scene.
- [ ] Crosswalk labels 1–4, pair assignment, preview, region editor and save/restart are valid.
- [ ] Junction drag has no initial jump; edge controls do not overlay text.
- [ ] Legacy pages are hidden but remain reachable in code; new Zones page is blank.
- [ ] Dashboard, Camera Settings and Crosswalks have no test-ready labels; page titles are concise.
- [ ] Windows changed-tests startup, typecheck/build and live smoke pass; existing ESP and configuration remain intact.

## Prior acceptance history

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
- [ ] Owner confirms PASS, otherwise `0_4_0` remains accepted baseline.
