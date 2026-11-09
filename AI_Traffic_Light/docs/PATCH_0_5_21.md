# Patch 0_5_21 — Same-source ambulance confirmation

Candidate `0_5_21`, previous `0_5_20`, accepted baseline `0_5_0`. Branch `feature/interactive-3d-simulation`.

Emergency evidence must include two distinct valid, positive camera frames at least 1,000 ms apart from the same source. Positive observations from different camera views alone never confirm a route. Existing protected phases and hardware-disabled behavior are unchanged.

New deterministic regression: `python scripts/test_v0521_ambulance_single_source.py`. Re-run V0519 and V0512 emergency regressions and coordinator conflicts. This is software-only. CI, Windows startup, camera realism and owner PASS remain pending.
