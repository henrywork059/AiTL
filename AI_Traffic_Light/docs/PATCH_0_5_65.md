# V0565 — Fixed-step legacy simulator adapter

Candidate `0_5_65`; previous `0_5_64`; accepted baseline `0_5_0`; Update 21 / S02.

## Implementation

CameraFrameService delegates timing to a small LegacySimulationAdapter under the existing owner lock. Elapsed monotonic time is represented in integer nanoseconds, accumulated and committed only in 50 ms steps; the old per-refresh fractional step is eliminated. The adapter exposes reset, explicit step, sync, pause, stop and immutable clock snapshot (time, pause, seed). The existing service retains world initialization, seeded RNG, agent movement, render/cache, observation identity and protected signal rules. One existing phase evaluation is shared by both movement types per committed step. Optional constructor-only seed and monotonic clock injection enable reproducible tests without changing HTTP endpoints; production retains the wall-clock-derived default seed. Existing private clock fixture seam is forwarded to the adapter. No new dependencies or physical outputs.

## Validation

Executed three isolated unittest cases against the exact new adapter on Python 3.13.5: different poll partitions (20 identical fixed steps over one second), pause/resume with preserved remainder, capped catch-up, backwards monotonic guard, reset and invalid durations. Both isolated Python files compiled. Verified Git blob hashes: adapter bed0c3ef779d3f4d3a63df10449a0ff940881904; regression 18a9deeff86bc1fb4fd688921cca114e85eca5d6. A fourth regression exercises actual legacy camera agents with injected clock/seed and fixed synthetic phase; it has not been executed locally. Full checkout unavailable due to GitHub DNS failure, so camera integration, old API/signal regressions and current full CI pending. Previous [0_5_64 full CI](https://github.com/henrywork059/AiTL/actions/runs/45619974507) passed. Owner PASS pending.

```powershell
# From AI_Traffic_Light
python scripts/test_v0565_simulation_adapter.py
python scripts/test_camera_frame_service.py
python scripts/test_camera_simulation_api.py
python scripts/test_v0515_3d_simulation.py
```

## Limitations and next gate

This is a legacy scheduling adapter foundation, not a complete replacement engine. Same seed and elapsed schedule with equivalent phase inputs and no gap over the two-second catch-up bound produce the same committed movement steps; elapsed time above that bound is deliberately discarded, and pause transitions discard uncommitted time since last sync as before (already accumulated substep remainder is retained). Live progression is still demand-driven; it is not an independent background worker, and existing adaptive rule evaluations and evidence expiry still use real time. Scene clock/agents and 2 Hz cached PNG may differ within a render tick; existing API semantics and source IDs are unchanged. Agent lifecycles, renderer, network experiments, and policy are unchanged. The internal clock adapter is only invoked by the camera owner in enabled mode; stop is not an external command interface. No SUMO execution or physical safety claim.

Security gate: previous CI audit JSON (run 45619974507, 25 Nov 2026) identified two high-severity vulnerable packages: locked source-map-js 1.2.1 ([GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), patched range starts at 1.2.2) and direct Vite 8.2.1 ([GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm), audit suggested Vite 8.3.8; additional lower-severity Vite advisories listed in the CI log). The audit step is non-blocking, exited 1, and is not a security PASS. No dependency changes here; package remediation requires regenerated lockfile and fresh audit/build/test evidence. Restrict prototype development server to trusted local access; do not expose it to untrusted networks or open untrusted projects/source maps. Security remediation takes priority before new dependencies; real SUMO smoke and security gates remain blockers for Update 22.
