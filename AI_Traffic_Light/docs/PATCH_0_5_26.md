# Patch 0_5_26 — Inference worker lifecycle guard

Candidate `0_5_26`, previous `0_5_25`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

If a running inference call outlasts the two-second shutdown join, the former stop() logic removed its thread reference while the thread was still alive. A subsequent start() could then clear its stop flag and run a second concurrent worker. Retain the reference until the old worker has actually exited. Cache clearing remains unchanged, and a later clean start is permitted.

Regression: `python scripts/test_v0526_inference_worker_lifecycle.py`. Also validate V0524/V0525 inference regressions, structure, CI, Windows startup and real camera/model stop/restart. No physical traffic-control changes. Candidate only; owner PASS pending.
