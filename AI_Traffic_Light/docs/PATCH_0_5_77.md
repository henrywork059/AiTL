# V0577 — Independently qualified simulator waiting-time measurement (Update 28A)

Candidate `0_5_77`; previous `0_5_76`; accepted baseline `0_5_0`. Update 28A only: software measurement and explicit comparison verdict qualified, not production wait equivalence or full S04 closure. All 39 original roadmap milestones retain their prior status; 30/39 delivered. Owner PASS remains pending.

Exact application HEAD `f88994700d08e2b54222dbd6d94e6c71f0546658`: [standard CI 46039170194](https://github.com/henrywork059/AiTL/actions/runs/46039170194) and [native CI 46039170178](https://github.com/henrywork059/AiTL/actions/runs/46039170178) passed every step. [Actual native evidence archive 15218724611](https://github.com/henrywork059/AiTL/actions/runs/46039170178/artifacts/15218724611) independently downloaded and SHA-256 matched `760ebf4d0a51238d3cac6d5d287293937b319614103cce04d4786d0a9432e85b`. Exact verifier Git blob `6d204dcdba410ce32b4da30326b8dc0dfb05eed0` executed locally; a second independent per-agent consecutive-interval implementation grouped episodes and reconciled all 8 x 2500 frames (20,000 timeline samples), 99,642 agent observations and 222 completed/censored episodes, every queue sample, episode duration, peak and integral, raw timeline digest and within-engine trace-repeat hash. Seed 42, 500 s, 0.2 s sampling, two repeats per arm. Actual executed synthetic simulations, not field data.

| Trial | Left vehicle / pedestrian wait (agent-s) | SUMO vehicle / pedestrian wait (agent-s) | SUMO minus left (agent-s) |
| --- | --- | --- | --- |
| Legacy motion vs SUMO (unmatched demand and geometry) | 1112.2 / 1761.0 | 129.4 / 15.4 | -982.8 / -1745.6 |
| Finite reference vs SUMO (matched offered demand and service gates) | 144.0 / 57.2 | 129.4 / 15.4 | -14.6 / -41.8 |

Finite arms both observed 8 vehicle passages and 14 pedestrian crossings. The finite reference is not production legacy; motion/path dynamics differ. The normalized stationary-approach wait contract counts consecutive 0.2 s observations within [-1,0) on the same gate/span with normalized displacement speed at most 0.01 gate lengths/s, excluding discontinuous visits and separating censored episodes. This is not the historical blocked-motion or desired-speed-deficit metric. Measurement replay and within-engine repeatability PASS; exact totals unequal; production historical wait parity NOT ESTABLISHED. No superiority claim or arbitrary equivalence margin. No runtime/controller/API/firmware changes, saved-data migration or simulator default switch. S04 remains gated on production compatibility and other outstanding requirements. No public-road authority. Exact release-bundle CI and owner Windows acceptance remain separate.

## Owner validation

From repository root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify footer `0_5_77 Candidate`, normal legacy simulator and unchanged saved profiles. Focused offline test: `python AI_Traffic_Light/scripts/test_simulation_gate_metrics.py`. To audit the downloaded CI ZIP from the repository root: `python AI_Traffic_Light/scripts/verify_s04_evidence.py <archive-path> --tamper-check` (see CLI help for optional SHA-256). Retain the documented digest and do not treat synthetic results as owner or physical acceptance. No unrelated development is authorized by this release.
