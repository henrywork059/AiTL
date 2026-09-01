# V0311 / 0_3_11 — Owner-confirmed passed baseline

Acceptance date: 2026-09-01

The owner explicitly confirmed that V0311 / `0_3_11` is running correctly and passes the project validation/acceptance workflow.

Release state after this acceptance:

```text
version: 0_3_11
previous_version: 0_3_10
passed_baseline: 0_3_11
status: owner-confirmed passed baseline
```

This acceptance covers the V0311 Junction Network feature and the same-candidate workflow/code hardening present on `main` at acceptance time. It does not change the documented prototype-only safety boundary and does not imply simultaneous multi-junction inference or public-road signal authority.

Future normal patch development should use `0_3_11` as the passed baseline. Increment `Z` only when the owner explicitly requests the next patch/version.
