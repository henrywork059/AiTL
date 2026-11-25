# 0_5_59 — Unified camera observation identity

Candidate; roadmap Update 15 / A02. Previous 0_5_58; accepted baseline 0_5_0.

## Implementation

Internal immutable `ObservationIdentity` projects the existing camera frame's original source ID, PC receive timestamp, frame number, original image dimensions and provenance. Managed ESP frames carry the existing session generation and source retirement epoch; synthetic primary/mirrored frames carry the render's mode generation. Ordinary HTTP uploads are unverified external input. Selected cache promotion retains the same frame and identity. The inference cache uses the shared frame key without changing its semantics. Existing manager lifetime/freshness checks, public JSON, crosswalk detection dictionaries, source coordinates, and selected-source control boundary remain unchanged. Generation metadata records acquisition, not current eligibility; the manager's existing token remains authoritative. Recent valid cached physical frames may still be restored after mode switches with original identity/time, not re-timestamped. No simultaneous multi-junction fusion, physical output or firmware change.

## Validation

Seven isolated contract assertions and isolated module compilation passed locally. New producer integration regression and existing freshness/safety regressions require full CI; local checkout unavailable (GitHub DNS blocked). Previous candidate CI passed (run 45517777657). Owner Windows/ESP PASS pending; baseline remains `0_5_0`.

Run `python scripts/test_v0559_observation_identity.py`, `python scripts/test_v0547_cached_frame_identity.py`, `python scripts/test_v0548_observation_invalidation.py` and `python scripts/test_v0550_signal_stale_fallback.py`. Existing physical lighting/speaker gates remain BLOCKED. Next: Update 16 / A03 transport/lifecycle separation, subject to CI and roadmap gates.
