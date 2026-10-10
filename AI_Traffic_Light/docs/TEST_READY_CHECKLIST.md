# V0317 Test-Ready Checklist

```text
version: 0_3_17
previous_version: 0_3_16
passed_baseline: 0_3_11
status: AI workflow efficiency candidate
```

## Agent workflow and documentation

- [ ] Short agent path locates owner, nearest test and contract without whole-repository reading.
- [ ] Narrow file reads and reuse of unchanged content are specified.
- [ ] Minimal diffs and avoidance of unrelated refactors/duplicate implementations remain required.
- [ ] Focused checks precede broader checks; failures/shared safety contracts trigger escalation.
- [ ] GitHub direct atomic commit, remote HEAD recheck and no-force push are documented.
- [ ] Documentation-only path avoids speculative application/firmware changes.
- [ ] Release-state, single-source inference, signal safety, API/data, runtime preservation and owner acceptance gates remain intact.

## Repository / owner validation

- [ ] `python scripts/check_structure.py` passes.
- [ ] Full standard Windows `update_test_run.ps1` validation passes on the owner's PC.
- [ ] Version/reporting surfaces identify `0_3_17`, previous `0_3_16`, and passed baseline `0_3_11`.
- [ ] Owner explicitly confirms PASS before promotion.

`0_3_11` remains owner-confirmed baseline until that confirmation.
