# V0320 Test-Ready Checklist

```text
version: 0_3_20
previous_version: 0_3_19
passed_baseline: 0_3_11
status: Crosswalk configuration candidate
```

- [ ] Crosswalks page and two-sided pedestrian crossing schematic render.
- [ ] Multiple crosswalk definitions can be added, edited, removed and reloaded from saved JSON.
- [ ] Opposing sides independently assign different saved ESP sources, or None.
- [ ] A missing camera profile displays a warning without silently clearing it.
- [ ] Save errors and unsaved changes are explicit; status polling does not reset edits.
- [ ] Crosswalk service and frontend structure tests pass.
- [ ] Structure checks, frontend typecheck/build and full Windows runner pass.
- [ ] Owner confirms PASS; `0_3_11` remains accepted until then.
