# Patch 0_5_22 — Network fail-closed resilience

Candidate `0_5_22`, previous `0_5_21`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Virtual network signals now fail closed on contradictory lamp/phase data and hold a connected movement red when a conflict-linked neighbor's signal state disappears. Existing clearance and priority rules are retained; no physical signal output.

Run `python scripts/test_v0522_network_disconnect.py` with existing V0514 conflict and V0519/V0521 emergency tests. No hardware control is introduced; existing configured-movement conflict semantics remain. Local Windows, any ESP device and owner PASS are still required.
