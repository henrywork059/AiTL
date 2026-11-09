# Patch 0_5_25 — Per-camera inference diagnostics

Candidate `0_5_25`, previous `0_5_24`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Expose measured per-camera inference latency, source frame age and freshness in the existing inference response and Camera AI Preview. Diagnostics are per-source and never fabricated; stale/mismatched-model frames are unavailable for AI overlay. Existing signal decisions and physical-output restrictions are unchanged.

Additive `GET /api/inference/cameras/{source_id}` diagnostics and Camera AI Preview source readout. Run `scripts/test_v0525_camera_diagnostics.py`, V0524 source ordering, inference, 3D and API regressions. Physical camera latency, model throughput and Windows operation are not verified until owner testing.
