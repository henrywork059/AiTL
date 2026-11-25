# V0562 — Source-qualified traffic observations

Candidate `0_5_62`; previous `0_5_61`; accepted baseline `0_5_0`; Update 18 / A03.

## Implementation

Selected-source analytics now preserve original source ID, explicit junction mapping, acquisition timestamp/frame and provenance in newly recorded flow events. Flow JSON returns per-source/junction/provenance summaries without cross-camera summation; historical aggregate records remain readable with unknown attribution. The additive traffic_observation projection reports sampled region occupancy, stationary waiting candidates and unavailable state with null metrics. The queue heuristic uses an 8-reference-pixel radius for at least 1000 ms in a configured waiting/queue zone, not calibrated speed or a verified traffic queue. New occupancy history samples retain attribution. Existing aggregate summaries, CSV columns, zones, selected-source architecture and virtual signal authority remain unchanged.

## Limitations

No simultaneous tracking or independent live observations for inactive sources; no unique-object fusion. Stationarity is sampled image-space evidence; unconfirmed objects may still be waiting, and region geometry/calibration are user configured. Lifetime is checked before tracking and before persistence/projection; concurrent source switching and inference remain nontransactional. Existing aggregate history and CSV retain legacy semantics. External uploads are not verified ESP observations. Physical lighting/speaker and actual ESP measurements remain blocked/outstanding.

## Validation

Locally executed 18 isolated helper cases using stub camera/manager and identity interfaces; compilation passed and Git blob 88909a0b47fc7c427e46609ed430a21278e06c0d matches. Initial isolated test fixture had an incorrect nested retirement token and was corrected before the passing run. Full checkout unavailable due to GitHub DNS failure; new integration regression and full CI pending. Previous CI passed (run 45555018709). Windows/ESP owner PASS pending.

```powershell
python scripts/test_v0562_traffic_observations.py
python scripts/test_v0561_tracking_scope.py
python scripts/test_object_tracking_flow.py
python scripts/test_zone_traffic_services.py
python scripts/test_traffic_history_service.py
python scripts/test_junction_network_overview.py
python scripts/test_v0550_signal_stale_fallback.py
```

Next Update 19 / A04: centralized frontend data access, subject to CI.
