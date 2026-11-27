# Patch 0_5_56 — Fake-only bench output abstraction

Candidate `0_5_56`; previous candidate `0_5_55`; accepted baseline `0_5_0`; roadmap Update 12 / H07. Branch `feature/interactive-3d-simulation`.

## Preflight

Verified previous candidate HEAD `04ba2118fd9c25af213e9d5f34e825f7033b8092` and successful GitHub Actions run [45431659801](https://github.com/henrywork059/AiTL/actions/runs/45431659801). Owner acceptance remains pending.

## Implementation

Added isolated `apps/pc-studio/backend/app/services/bench_output.py`. A controller is disabled by default and accepts only the in-memory fake adapter. The test harness must opt in explicitly, connect the fake adapter and arm with `authorized=True`. This boolean is a local software test gate, not a hardware authorization or security boundary. There is no live service instance, route, UI command, firmware change, GPIO, network transport or physical driver. The existing camera registry, capability contract and traffic-control boundaries remain unchanged.

The sole supported fake capability is `demo_indicator`; traffic signals and physical lighting/speaker capabilities are not accepted. Commands carry a monotonically increasing controller-local ID and integer lease duration of 1–2000 ms. The fake acknowledgment must match the ID, accept the command and satisfy a 100 ms acknowledgment bound and the lease deadline. An overlapping command, unsupported capability, invalid duration, missing/rejected/wrong/late acknowledgment or adapter exception fails closed and disarms. Explicit off, disconnect and watchdog lease expiry also disarm. A fresh explicit arm is required before another command. A connection-generation change also clears prior arming even when the intervening disconnect and reconnect occurred between watchdog checks.

A monotonic lease is checked on every controller operation, explicit watchdog tick and fake-adapter active-state read. This is deterministic software lease expiry, NOT an autonomous watchdog thread, hardware interlock, or guarantee of physical de-energization during a process hang. Acknowledgment faults are synthetic; no real communication latency, device power or electrical safety has been tested. The chosen lease/acknowledgment limits are conservative prototype test defaults, not certified hardware limits.

## Validation

Ran the exact new regression locally: `python scripts/test_v0556_bench_output.py` (8/8 passed). Python compilation passed. Tested disabled/unauthorized requests, unsupported/invalid durations, acknowledgment correlation and faults, lease expiry, overlapping requests, explicit off, disconnect/rearm and expiry without controller tick, and unobserved reconnect invalidation. GitHub file blobs match locally tested sources. Full CI to be verified on the candidate.

## Owner acceptance

From repository root in PowerShell:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

No hardware attachment or actuation is required or permitted for this candidate. Update 13 requires explicitly confirmed lighting hardware, electrical/interface specifications and controlled-bench authorization before any real adapter is added; otherwise keep physical lighting unavailable and document the blocker.
