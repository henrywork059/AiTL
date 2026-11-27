# Patch 0_5_51 — Emergency evidence and virtual network clearance

Candidate `0_5_51`, previous `0_5_50`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap Update 07 / A01.

## Root cause and change

Preserve a released movement's two-second virtual clearance record even when the crossing receives a compatible new grant; overlapping release histories conservatively protect both movement types. Sanitize contradictory lamps even without configured links. Emergency confirmation requires two distinct fresh frame IDs from one source at least one second apart, correct model identity and current wall-clock freshness. Withdraw pending priority on lost confirmation, stale evidence, route removal or timeout; retain already committed phase durations and protected local transitions.

Only explicitly configured conflicts are supervised. Pending requests are withdrawn, not already committed green extensions. Ingestion currently advances controller status before updating new camera evidence; previously applied timing is not reversed. Dynamic conflict topology edits may still clamp virtual output and are not certified safe; software-only, no physical signal actuation. Explicit route removal or lost confirmation cancels pending requests at next status/ingestion. No verified real emergency identity or field safety claim.

## Validation

Local Python 3.13.5: original coordinator source matched GitHub FNV-1a f9c8e054; reproduced two defects (compatible grant erased clearance and standalone invalid lamp passed through). Patched coordinator whole module df44e28b and new evidence helper 6152a7b8 executed locally: six targeted coordinator checks plus 64 configured movement/conflict pairs and seven emergency evidence cases all passed. No service integration or physical testing claimed. Added test_v0551_emergency_interlocks.py including pending-priority withdrawal integration cases; full regression not executed. Direct GitHub ls-remote failed DNS resolution; CI and owner Windows/ESP PASS pending.

Run `python scripts/run_offline_tests.py --focused test_v0551_emergency_interlocks.py test_v0512_emergency_corridor.py test_v0514_network_conflicts.py test_v0519_emergency_evidence.py test_v0521_ambulance_single_source.py test_v0522_network_disconnect.py` and the complete suite. Next: Update 08 / H05, camera transport diagnostics.
