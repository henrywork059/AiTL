# Patch 0_5_50 — Stale-input virtual signal fallback

Candidate `0_5_50`, previous `0_5_49`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap Update 06 / A01.

## Root cause and change

Adaptive camera observations use original source receive time, bounded by the shorter of the configured timeout and five seconds; missing, future, expired and explicit unavailable inputs are rejected. Replay cannot renew the same timestamp. Persistence is reset after stale/fixed/unavailable evaluations or an elapsed observation gap, even without polling. Unverified named classes are unavailable instead of assumed zero. Fused crosswalk policy observations use the oldest contributing view. Already-committed phase duration and protected transition sequence are preserved; no physical output.

Camera observations lack explicit model class vocabulary; a class absent from all observed regions is conservatively unavailable even when the loaded model may support it. Generic synthetic/Test inputs retain existing semantics. A stale observation withdraws new adaptive adjustments, not a previously committed extension or incident hold. Previously forwarded observations can remain active until the controller receives invalidation or reaches their source-time expiry; ingestion/status ordering and emergency/network evidence and conflict interlocks remain follow-up audit boundaries. Emergency/network interlocks are Update 07. Mode and source identity limitations from prior candidates remain; this is virtual control only, not certified traffic safety.

## Evidence

Five defects reproduced with four copied original method blocks matched to GitHub by FNV-1a. Ten patched isolated behavioral checks passed (expired, unavailable, future/missing, replay, stale persistence, unavailable persistence, unpolled gap, unknown class, five-second cap, explicit Test mode). Patched block hashes: observe/clear/freshness 6d63a0c9, condition value 59d80e9b, candidate evaluation 1157b7a2, observation values 9965254b. Test harness injected clock, constructor, memory and scenario-match dependencies; this is not full controller or integration testing. The repository regression includes the real protected phase sequence and fused-view age checks; not executed locally. The changed-test selector regression also executed successfully, with source hashes 75004545 and 1c8e6d9f; compileall of the local harness and selector files passed. Direct clone still fails DNS; full CI/Windows/ESP owner PASS pending.

Run `python scripts/run_offline_tests.py --focused test_v0550_signal_stale_fallback.py test_signal_rules_service.py test_signal_scenarios.py test_v0512_camera_crosswalk.py test_select_changed_tests.py` from the project directory with backend dependencies, then the full suite. Focused signal source changes conservatively select the complete suite. Next: Update 07 / A01, emergency and network interlocks.
