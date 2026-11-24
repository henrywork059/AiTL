# Patch 0_5_46 — ESP worker retirement and recovery

Candidate `0_5_46`, previous `0_5_45`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap [Update 02 / H02](ROADMAP.md#4a-numbered-update-by-update-implementation-queue).

## Root cause

The stop helper cleared connected state after joining even if a replacement had started. A late exception or EOF could update failure counters/status; recovery could publish stale status and issue config/start after retirement. A frame sink returning late could also record success against the new worker.

## Change

Guard retired-worker failure, join completion, receive counters/frame metadata and recovery using the worker stop-event identity. Serialize recovery with replacement ESP control commands and recheck ownership around each HTTP stage. Already-issued HTTP calls may finish before replacement control; their stale responses cannot publish state. A frame sink already in progress is not rolled back; cache/source provenance remains Update 03/04.

The join retains its 2.5-second timeout. No firmware, TCP framing, public API or traffic signal changes; no physical actuation. An already-issued control request cannot be revoked, and HTTP retries remain bounded by the existing policy. This does not serialize every possible concurrent user API action.

## Validation

Original isolated method probes reproduced stale join status and stale recovery publication/rearm, and confirmed failure recording lacks a worker guard. The patched methods passed 11/11 isolated behavioral checks with injected dependencies (four transport cases, one join, five recovery cases and one late frame sink); the copied method blocks were hash-matched to the staged source. Direct clone blocked by DNS. Full-module tests, CI for this candidate and owner Windows/ESP acceptance are not yet verified.

Focused regression: `scripts/test_v0546_worker_retirement.py` (11 deterministic cases: delayed open/read exception, OSError/EOF, timed-out join boundary, recovery status/config/start/error and normal recovery, late sink return). Updated V0544 fixture to exercise worker identity. Run V0544, V0545, V0546, remote-camera integration regressions and full runner before owner PASS.

Next: Update 03 / H03, cached-frame timestamp/source provenance.
