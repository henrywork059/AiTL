# Patch 0_5_28 — Reconnect-safe ambulance evidence

Candidate `0_5_28`, previous `0_5_27`, accepted baseline `0_5_0`. Trust strictly newer source timestamps for emergency-evidence freshness even if a camera reconnect resets its frame counter. A negative reconnect frame clears older ambulance evidence, while equal/older timestamp replays remain rejected. Confirmation still requires two distinct positive observations at least one second apart from the same camera; protected virtual traffic signals and disabled physical outputs are unchanged.

The global camera inference worker already accepts newer timestamps after frame-number resets (V0524), but the independent Crosswalk ambulance evidence gate still rejected any frame with a lower counter. This could suppress fresh positive evidence and ignore a new negative after reconnect. Its existing per-source timestamp guard now decides freshness; source/model and positive-observation rules remain unchanged.

Regression: `python scripts/test_v0519_emergency_evidence.py` (reconnect positive, reconnect negative and old-timestamp replay), `python scripts/test_v0521_ambulance_single_source.py`, `python scripts/test_v0524_camera_source_order.py`. CI compile/structure/full offline regressions/frontend typecheck/build and owner Windows/ESP acceptance remain required. No API, data schema, model, network topology or physical-output changes.
