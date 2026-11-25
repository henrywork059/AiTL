# 0_5_61 — Scope selected-source tracking by camera and junction

Candidate; roadmap Update 17 / A03. Previous 0_5_60; accepted baseline 0_5_0.

## Implementation

The existing selected-source tracker now uses an internal scope of camera ID, explicitly matched junction (unmapped remains None), original image dimensions, provenance and acquisition generation/epoch. A scope change, frame-number reset or gap over five seconds starts new tracks; no identity is carried between sources or junctions. A bounded 256-source watermark prevents previously processed cached frames from advancing tracking after switching or active reset. Current same-frame threshold requests may annotate without advancing. Live callers supply immutable ObservationIdentity; expired/mismatched frames receive no tracking annotation, and tracking status endpoints suppress non-current scopes. The existing per-source frame timestamp and five-second freshness policy are reused. No inactive tracker continuation, new inference pipeline, cross-camera fusion, signal policy changes or new public fields. Existing flow events remain legacy aggregate history; independent traffic observation/flow semantics are next in Update 18. Watermarks are process-local and bounded, and an evicted source loses its replay history; no global unique-vehicle claim.

## Validation

Locally executed the isolated TrackingContinuity helper: 16 targeted assertions plus a bounded-source loop; compilation passed. The helper's staged blob must match the locally tested hash. Full producer/route/tracker regressions were added but not run locally: GitHub DNS resolution failure reproduced. Previous candidate corrective CI passed ([run 45538583036](https://github.com/henrywork059/AiTL/actions/runs/45538583036)); current CI and Windows/ESP owner acceptance pending. Physical throughput/CPU comparison and lighting/speaker gates remain outstanding.

Run `python scripts/test_v0561_tracking_scope.py`, `python scripts/test_object_tracking_flow.py`, `python scripts/test_zone_traffic_services.py`, `python scripts/test_v0547_cached_frame_identity.py` and `python scripts/test_v0550_signal_stale_fallback.py`. Next Update 18 / A03: independent traffic observations, subject to CI.
