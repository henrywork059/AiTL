# Patch 0_5_11 — Independent Crosswalk Signal Controllers

**Candidate:** `0_5_11`; **previous:** `0_5_10`; **accepted baseline:** `0_5_0`.

## Implementation

- New crosswalk-keyed simulation runtime registry reuses existing protected `SignalRulesService` and shared persisted scenario definitions, with separate clocks/phase/decision/incident state and history logs.
- New read-only `GET /api/traffic/crosswalk-signals` and frontend Network polling display independently computed pedestrian/vehicle signal state for every saved crossing.
- Save/delete Crosswalks is reconciled at next status read; simulation stop removes active controllers. Existing old signal APIs and global simulation remain in place.
- Network metadata exposes crosswalk neighbor IDs but does not command or imply safe coordination. Per-crosswalk camera observations remain an explicit future integration point, not fabricated data.

## Limits

No automatically inferred conflicting movements, coordinated phase arbitration, physical signal actuation, or guaranteed camera-to-crosswalk observation binding. The controller registry is simulation-only.

## Testing

Added `scripts/test_v0511_crosswalk_signals.py` and `scripts/test_v0511_crosswalk_signal_wiring.py`, updated prior structure assertion. Full Windows tests/build/smoke and owner PASS pending. Accepted baseline remains `0_5_0`.
