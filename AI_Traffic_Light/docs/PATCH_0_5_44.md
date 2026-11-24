# Patch 0_5_44 — ESP TCP post-read cancellation boundary

Candidate `0_5_44`, previous `0_5_43`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

## Root cause

The ESP receive loop checked stop/simulation state before its blocking read, but published any non-EOF result without rechecking. A state change during the read could therefore allow one obsolete frame through or misclassify a simulation-switch EOF.

## Change

Recheck the worker stop event and current simulation mode immediately after a blocking TCP packet read, before counting or publishing the returned packet. A normal complete packet and ordinary EOF retain their existing behavior. This is a narrow receive-loop boundary fix, not a guarantee of atomic cancellation across every worker or mode-transition path. No dependencies, firmware, wire format, endpoint contracts, 3D presentation or signal logic changed. Cancellation after the guard and wider worker-lifecycle races remain separate audit items.

## Evidence and acceptance

Six isolated cases of the exact receive-loop method with injected packet reader, stop event and simulated mode passed after the change (three failed before). This is not full-module or hardware validation. Repository test: `scripts/test_v0544_tcp_read_cancellation.py`. Run complete CI and owner Windows/ESP checks as described in LOCAL_TESTING; explicit PASS is required.
