# Patch 0_5_58 — Synthetic speaker preparation (physical integration blocked)

Candidate `0_5_58`; previous `0_5_57`; accepted baseline `0_5_0`; roadmap Update 14 / H07. Branch `feature/interactive-3d-simulation`.

## Preflight

Verified HEAD `0b65c8fb1792df5e16fe4e72ff1d2c43613df4b4`, VERSION and previous successful GitHub Actions run [45515165289](https://github.com/henrywork059/AiTL/actions/runs/45515165289).

## Implementation

The isolated `FakeSpeakerDemo` reuses the existing fake bench controller for a metadata-only demonstration of two predefined notices (`demo_attention`, `demo_accessibility`). Integer normalized volume 1–100% and duration 1–2000 ms are synthetic test bounds, not acoustic levels or certified limits. Explicit test arming is required; invalid or overlapping commands, acknowledgment faults, off, disconnect, generation changes and expiry clear the active notice. No audio playback, arbitrary speech, live route, UI, GPIO, network or firmware integration.

The two notice texts explicitly say "Demonstration only" and do not grant crossing permission. No text-to-speech, recordings, tone synthesis or audio device access is provided. The volume percentage is metadata only, not a decibel value. The existing controller is unchanged; facade operations serialize metadata and use the existing acknowledgment/lease checks. The active prompt and volume are cleared when a request fails, the output is stopped, or the controller reports inactive. The adapter's software watchdog is not an independent physical fail-safe. This is an isolated test harness; no application instance, persisted setting, endpoint or physical capability is added. No concurrent lighting/speaker physical arbitration is established.

## Hardware gate

Physical speaker integration is BLOCKED: hardware model, amplifier/driver, electrical specifications, acoustic limits, independent hardware fail-safe and controlled-bench authorization remain unconfirmed or unavailable. No acoustic or physical safety validation was performed. Physical lighting also remains blocked. The next independent roadmap item is Update 15 / A02. Keep both physical output gates open in the backlog.

## Validation

Ran `python scripts/test_v0558_bench_speaker.py` (7/7), `python scripts/test_v0557_bench_lighting.py` (6/6) and isolated Python compilation in the local subset of the repository. Existing bench and lighting source/test blobs were verified against the prior branch commit; both new Git blobs exactly match locally tested files. Coverage includes default authorization, synthetic provenance/expiry, invalid input including non-string prompt and non-integer volume, overlap, acknowledgment faults, explicit stop, disconnect and unobserved reconnect. The full local suite, structure, frontend build, Windows acceptance and hardware checks were not run locally. Current GitHub Actions result is separate.

## Owner acceptance

From repository root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

No physical hardware attachment or audio playback is required or authorized. Owner PASS applies only to this software candidate.
