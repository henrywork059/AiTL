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

---

# V0576 — Capture freshness, managed dataset integrity and independent S04 evidence candidate

Candidate `0_5_76`; previous `0_5_75`; accepted baseline `0_5_0`. Reconciled authorized HEAD 00f4d542c20899816758114b012e83650a8e9263 retained, including 8 MiB bounded upload regression and historical main integration. Concurrent P3/P4/P5 independent candidate; Updates 30/33/37/38 remain partial, S04 / Update 28 gated. Delivered milestones remain 30/39 (76.9%), not acceptance.

From repository root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify footer 0_5_76 Candidate. With disposable reviewed captures and authorized controlled cameras, check expired/source-switched capture rejection, fresh/paused simulation capture, saved SHA, evaluation-only exclusion, managed build/review and rejection of corrupted/missing-manifest data. Rebuild old managed datasets explicitly from saved reviews if requested; original captures stay intact. Run training only with approved local dependencies/weights/data; the fake trainer and browser fixture are not actual model validation. Verify protected simulation/physical transitions and saved profiles. Explicit owner PASS required.

Application CI 46030780891 passed on 6bf86a149f330ead6a7920e2449bfaad2a7d8dc3 (126 offline scripts, independent evidence verification, frontend regression/typecheck/build and blocking audit). Existing bounded upload test passed. Initial P3/P4/P5 push/PR CI 46030002243/46030011877 passed; intermediate CI 46030592921 passed. Managed service regression rejects modified copied images/labels, untracked split files, changed original bytes, path alias bypass and missing marked manifest, then admits verified data with deterministic fake trainer; no weights loaded. Real-clock Windows Edge browser CI 46030781055 passed capture, training, review, junction, region and renderer workflows including verified dataset identity. Artifact 15213763479 SHA-256 49b413d570dbdbef84dc106b06b9acb6d1ecc49f03027a5cbf0f224eb82b55b3; capture and training screenshots inspected; synthetic API responses and pre-version-bump footer 0_5_75. Fresh native CI 46030002341 passed; archive 15213988017 SHA-256 6d9342e98d7c5f58b7532f38fd73af99a6ddc1c11af48c441e6e0a6317850d2a verified independently, 44 new capture content digests matched, actual native detail screenshot inspected. Integrated native audit CI 46030592878 passed completely.

S04: standalone stdlib verifier scripts/verify_s04_evidence.py exact locally tested Git blob 06c16b163d90bde25bc9e5736f5272f6275f8247 accepts directory or archive plus independent SHA-256; audits 20,000 normalized samples over eight repeated CSV timelines, corresponding raw summaries/digests, six 400+400 HTTP workloads (raw scene/frame mean and linear p95, process working-set sums and CPU deltas), 11 capture archives and 44 synthetic coordinate views, four mirrored half-open footprint transforms, content/inner/outer hashes and nonauthority flags. Three nonmutating negative controls rejected changed wait, latency and capture digest. Locally verified old archive 15204881978 and fresh 15213988017, plus integrated CI audit. Fresh resource mean frame latency: indexed lean 10.4560 ms, RGB lean 17.6045 ms, indexed spawn 11.3491 ms (800 frame reads/configuration); mean final combined working sets 158711808, 173279232, 210978816 bytes. Nonrandomized Windows CI diagnostic workload, not owner budget. Finite native/reference passages each 8 vehicle and 14 pedestrian crossings; waits 129.4 vs 144.0 vehicle-agent-s and 15.4 vs 57.2 pedestrian-agent-s; not equivalent. Palette-only synthetic control canonical vehicle 96/96 matched, pedestrian 40/43 truth and 40/41 predictions, not trained detector performance. No production calibration/common wait estimand, trusted trained holdout, owner Windows/ESP resource/rollback approval; S04 stays gated. Legacy remains default, native isolated evaluation only; no public-road authority.

---

# V0575 — Independent source-qualified capture, training-safety and evidence-verification candidate

Candidate 0_5_75; previous 0_5_74; accepted baseline 0_5_0. Independent concurrent P3/P4/P5 progress, partial Updates 30/33/37/38. Updates 31 and 36 remain delivered candidates from 0_5_74. 30/39 delivered candidate milestones (76.9%), not owner acceptance. Update 28 / S04 remains gated.

From repository root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Check footer 0_5_75 Candidate, two physical sources and simulation-mode handoff (authorized test only); verify no stale preview, Side A/B polygon save/fail/reload and real pointer hit, capture source-switch rejection with no file write, status-error recovery, managed dataset exclusion of evaluation-only samples, training ready/stale/failure recovery and raw evidence integrity. Use disposable test data and back up saved profiles. Do not run real YOLO training or connect public-road controllers as part of CI. Owner must explicitly confirm PASS.

P4 exact real-clock Windows Edge browser CI 46025031969 PASSED on application tree b6c0f1e2ca5584c81fd0758478e4f730cac959ce. It exercised actual pointer input, source-change capture rejection and recovery, decoded synthetic HTTP preview, stale/ready/error training transitions, saved crosswalk regions and side-specific vertex repaint, junction topology and source ownership, review labels/build/delete, render/rollback. Verified artifact 15210369050 SHA-256 6bf6a116c42999f2d226e3f0cdcb0473dbc3aff675920939278778ba964a1fba, with capture, training, crosswalk, junction and review screenshots actually inspected. Synthetic API and HTTP image fixtures only; not a physical ESP or trained detector. Standard CI 46022866121 PASSED full offline, seeded batch, build/audit at prior implementation tree; exact latest CI 46025214608 passed offline regressions including deterministic camera race correction, and was executing the seeded batch during release preparation. Release commit CI and owner Windows PASS remain pending.

S04 remains OPEN. Existing native archive 15204881978 and CI 46012562415 qualified 11 synthetic captures/44 mirrored decoded views with a palette control, not a trusted trained detector. Native/reference finite passages each 8 vehicles and 14 pedestrians, but normalized waits remain different: native/reference 129.4/144 vehicle-agent-s and 15.4/57.2 pedestrian-agent-s. Production coordinate calibration or explicit synthetic-only contract, common wait estimand, trained holdout/detector proof, owner-PC Windows/resource budget and rollback acceptance remain missing. Freeze optional geometry polish. Legacy simulator stays default; native trial is opt-in. No public-road actuation, stored-data migration, accepted baseline promotion, main merge, or owner PASS claim.

---

# V0574 — Independent network, region, AI review and reproducible experiment candidate

Candidate `0_5_74`; previous `0_5_73`; accepted baseline `0_5_0`. Updates 31 / U02 and 36 / E02 delivered as software candidate milestones. Updates 30, 33, 37 and 38 partial; Update 28 / S04 remains gated. Owner PASS pending.

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify footer 0_5_74 Candidate. Back up saved data before testing. Use disposable capture fixtures for destructive tests. Verify camera source selection and no stale preview, side A/B independent region drag/save/reload and failure retry, crosswalk links and camera reassignment/cancel, stale/unavailable status and draft retention, review identity/decode rejection, positive/negative label save, build and delete invalidation. Confirm legacy simulator remains default and existing optional renderer fallback/rollback. Run authorized bench checks only; no public-road outputs. Owner alone confirms PASS.

Application and test qualification: exact [standard CI 46018941752](https://github.com/henrywork059/AiTL/actions/runs/46018941752) on `9e006c900814f65e3e82c76db98fefb815144560` passed compilation, structure, full offline suite, seeded batch, frontend data-access tests, typecheck, build and blocking audit (zero vulnerabilities reported). [Browser CI 46016827486](https://github.com/henrywork059/AiTL/actions/runs/46016827486) on `f18cd41995fd30ef8be305d1d038bca37cc95942` passed all workspace and renderer tests. Later application-qualification commits changed only the two legacy static regression scripts, preserving side-selection and region invariants while checking the new handler. Browser artifact [15205454907](https://github.com/henrywork059/AiTL/actions/runs/46016827486/artifacts/15205454907) SHA-256 `1f672c0f1a6df01ff17b923d3328f60fee6d0960a0ceb9f6b8199071b4f17328` matched; actual region, junction and review screenshots inspected. Tests use synthetic API fixtures, not ESP hardware or trained-model inference. Exact release-bundle standard CI remains pending at publication.

Isolated 120 s queue-model comparisons: 4 seeds (42, 43, 73, 101), 3 demand levels, 12 matched cases, 36 primary policy rows, 96 intersection fairness rows, 4 busy repeats. [Exact standard artifact 15207277149](https://github.com/henrywork059/AiTL/actions/runs/46018941752/artifacts/15207277149) SHA-256 `421b2abbc180b1ded17904f72e61727b00624b1842cb5b36086c4c19292e0c93` independently matched, all 43 member hashes, 216 primary values and 1056 intersection values reconciled; repeated network/local metrics and scenario identity verified. Cooperative minus adaptive pedestrian wait increases in 4/4 light, 3/4 normal and 4/4 busy cases; busy mean +32.125 person-s, vehicle wait mean -305.875 vehicle-s. Secondary pedestrian-aware policy retains adverse cases and vehicle-wait tradeoffs. No tuning, statistical generalization or field claim. Add a standalone read-only evidence verifier (stdlib, no simulator imports) whose exact staged Git blob was matched to locally tested source. It passed two retained full CI archives, and rejected wrong external digest, altered CSV with original or recomputed member hash, and rehashed altered busy repeat. Integrate full batch verification into standard CI and focused smoke/tamper regression; these new CI integrations await exact release CI. Timeline/decision exports are hash-checked, not semantically replayed by this verifier.

Native qualification remains separate: [native CI 46012562415](https://github.com/henrywork059/AiTL/actions/runs/46012562415) and 46011851179 passed; 11 synthetic capture archives/44 images, palette control only, no trusted model holdout. Independently reconciled native/reference normalized timeline metrics and matched resource workloads remain documented in [SIMULATOR_MIGRATION_GATES.md](SIMULATOR_MIGRATION_GATES.md). Finite passage counts match 8 vehicles/14 pedestrians, but native/reference normalized waiting differs (129.4/144.0 vehicle-agent-s; 15.4/57.2 pedestrian-agent-s). Production coordinate calibration/common estimand, trusted detector validation, owner resource budget/Windows and rollback acceptance remain open. Legacy simulator remains default; no public-road signal actuation, no baseline promotion. Partial 30 owner live device/mode acceptance; partial 33 capture/training workflow; partial 37 trusted holdout; partial 38 endurance/master evidence. Updates 32/34 retain dependency gates.

---

# V0573 — Independent P4 hardware-first workspace candidate

Candidate `0_5_73`; previous `0_5_72`; accepted baseline `0_5_0`. Update 29 / U01 delivered as candidate; Updates 30–31 / U02 and 33 / U02 partial. Owner PASS pending.

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify version 0_5_73 Candidate, all navigation destinations and simulation toggle, narrow-window navigation and keyboard focus, unavailable dashboard states, saved camera selection/connect/retry/start/stop with authorized local bench only, no stale preview, crossing link save/reload and no conflicting signal authority, AI model filter/load/error/recovery using trusted local weights only. Check saved regions and dataset preservation. Verify legacy simulator default and optional renderer/editor fallback. Owner alone confirms PASS; no public-road outputs.

Application revision `58b88d4f119347fa8abfaabc592dff10dfaae781`: [standard CI 46008844336](https://github.com/henrywork059/AiTL/actions/runs/46008844336) passed all steps, including 126 discovered offline regression scripts, frontend data-access tests, typecheck, build and blocking npm audit. [Browser CI 46008844185](https://github.com/henrywork059/AiTL/actions/runs/46008844185) passed workspace, renderer and integration trials. Actual headless Windows browser renders of production components with synthetic API fixtures; not field evidence. [Artifact 15203510241](https://github.com/henrywork059/AiTL/actions/runs/46008844185/artifacts/15203510241) SHA-256 `3f88d3f71ef4c2c169eab84d2c2c34226e7e9727440ebe94a742f123b91fac41` independently matched. Corrected camera screenshot inspected: high-contrast empty preview, selected camera B connected but no received frame, stopped stream and camera A unchanged. Corrected network screenshot inspected: one saved link, selected crossing visible, inspector endpoints North [2] / South [4], no verified signal, no assigned cameras. Browser assertions cover camera selection, failed probe/profile retention, retry/start/stop, unverified-frame rejection, other-camera isolation, keyboard link creation/save/visible retention/API reload, model filtering/load/error/recovery, missing validation and responsive navigation/overflow. Exact release commit standard CI pending at publication. Prior native CI 45996915921 passed separately; not an S04 migration acceptance.

Update 29 / U01 delivered as a software candidate (navigation inventory, narrow/desktop browser and existing route/keyboard controls); 28/39 numbered milestones delivered as candidates (71.8%), not owner accepted. Updates 30, 31 and 33 remain partial: owner live Windows camera/editor and simulation-mode checks; comprehensive topology edit/delete, source assignment and stale observation workflow; capture/review/edit/export and training workflow acceptance, respectively. Network fixture proves UI/request/reload behavior; offline backend tests separately prove persistence and invalid-link rejection. Browser model activation uses mock API responses, not actual YOLO inference. Existing scrollable map can clip other nodes while selected node remains visible. Preserve existing light/dark tokens; no further optional restyling. S04/Update 28 remains open: legacy-compatible metrics, production coordinate calibration, trusted detector evidence, owner-PC matched resource/latency budget and acceptance, rollback and migration gates in [SIMULATOR_MIGRATION_GATES.md](SIMULATOR_MIGRATION_GATES.md). Updates 32/34 remain gated. No public-road signal actuation or accepted baseline change.

See [Patch 0_5_73](PATCH_0_5_73.md).

---

# V0572 — Isolated SUMO two-junction corridor and spillback

Candidate `0_5_72`; previous `0_5_71`; accepted baseline `0_5_0`; Update 27 / S04. Owner PASS pending.

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic simulation only; verify unchanged legacy default, optional Three.js view, pause/reset, camera A–D, editor vertex drag/save/reopen and no physical outputs. Corridor experiment is not visible in the default UI. Optional native validation uses the pinned Windows SUMO evaluation workflow or `.github/scripts/sumo_corridor_trial.py` with an output JSON path in the trusted isolated environment. Owner alone confirms PASS.

Application revision `807864fafaf14eab75721cebddb542943635c774`: [standard CI 45765997190](https://github.com/henrywork059/AiTL/actions/runs/45765997190) and [native SUMO CI 45765997178](https://github.com/henrywork059/AiTL/actions/runs/45765997178) passed. Native JSON inspected in job logs; [artifact 15091264465](https://github.com/henrywork059/AiTL/actions/runs/45765997178/artifacts/15091264465). Seed 42, two 800 s runs, step 0.2 s (4000 steps/run); identical SHA-256 digest d539ea50feb3d0501a7d638d6d04d82e297bc6e4dd0eca6b2ef41b48695a3d63 and all metrics. Per run all 16 distinct vehicle IDs observed entering and leaving AB then arriving; no duplicate snapshot IDs or active/arrived overlap, all 4 pedestrians arrived. Peak observed AB occupancy 4 vehicles; 324 blocked-admission checks with stopped upstream demand and connector front-bumper position below 12 m, of which 207 occurred during downstream all-red. 75 ticks with simultaneous nonempty grants and different requested phases; 4 authorized pedestrian crossing entries and 13 per-person CLEAR occupancy samples. Link travel time is measured from first sampled AB entry to first sampled internal B entry and includes waiting, not door-to-door journey time. Per-ID seconds: v0 109.8, v1 134.0, v2 133.6, v3 111.6, v4 29.0, v5 13.2, v6 13.4, v7 13.2, v8 11.8, v9 13.2, v10 13.4, v11 13.2, v12 12.0, v13 13.2, v14 13.2, v15 13.0. Offline corridor admission, prior native trials, lifecycle and mapping checks, standard compile, structure, offline regressions, frontend tests/typecheck/build and blocking audit passed. Executed synthetic simulation, not field evidence. Exact release commit CI pending at publication.

See [Patch 0_5_72](PATCH_0_5_72.md).

---

# V0571 — Isolated SUMO lane queues and turning scenarios

Candidate `0_5_71`; previous `0_5_70`; accepted baseline `0_5_0`; Update 26 / S04. Owner PASS pending.

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic simulation only. Confirm default legacy view, optional Three.js preview, existing pause/reset, camera A–D, and editor vertex drag/save/reopen; verify no change in coordinates or physical outputs. Do not expect turning traffic in the default view. Optional native evaluation requires the pinned Windows wheels and the existing SUMO evaluation workflow; run `.github/scripts/sumo_lane_trial.py` with an output JSON path only in the trusted isolated environment. Owner alone confirms PASS.

Application/test revision `b850a2a9077a96cbc4cfcd5931d5244eb84ac57b`: [standard CI 45764874498](https://github.com/henrywork059/AiTL/actions/runs/45764874498) and [native SUMO CI 45764874374](https://github.com/henrywork059/AiTL/actions/runs/45764874374) passed. Actual native JSON printed in job logs; evidence artifact [15091029072](https://github.com/henrywork059/AiTL/actions/runs/45764874374/artifacts/15091029072). Two runs, seed 42, each 440 s at 0.2 s steps (2200 steps); identical SHA-256 digest b5f4f58b81dad25f06447517a09062968c1c3fcebfe82d160d5242b6080946f7 and metrics. Per run: 626 stopped-queue ticks (at least two stopped west-approach vehicles), 577 ticks with a stopped vehicle within 8 m of the lane endpoint, 116 blocked-exit checks during vehicle green, 16 observed authorized vehicle entry transitions, 8 authorized pedestrian crossing-edge entry transitions, 21 pedestrian CLEAR continuation occupancy samples (per-person samples, not necessarily distinct ticks), 116 pedestrian crossing-occupancy ticks, both turn exits CN/CS observed, 17/17 vehicle arrivals including the exit blocker and 4/4 person arrivals. Admission, seeded demand, protected permissions, actual entry transitions and prior shadow lifecycle checks passed; standard compile, structure, offline regressions, frontend data-access tests, typecheck, build and blocking npm audit passed. Evidence is executed synthetic simulation, not field data. Exact release commit CI pending at publication.

See [Patch 0_5_71](PATCH_0_5_71.md).

---

# V0570 — Persistent articulated pedestrians and observed gait

Candidate `0_5_70`; previous `0_5_69`; accepted baseline `0_5_0`; Update 25 / S03. Owner PASS pending.

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic simulation only. Confirm legacy default, hide visible overlays if necessary, select Three.js preview; observe pedestrian approach, waiting, WALK/CLEAR, direction, pause/resume and reentry across A–D; test orbit/Top/Zoom/Reset and resize. Confirm no walking in place after observations settle. Select Legacy view, open editor, drag/save/reopen vertex and verify unchanged reference coordinates; re-enable overlays to verify fallback. Confirm no physical camera/signal output changes. Owner alone confirms PASS.

Application revision `40fcd2ea232ae4a79d16ca17d1b7a16e15cf510c`: [standard CI 45755422048](https://github.com/henrywork059/AiTL/actions/runs/45755422048) and [renderer CI 45755422084](https://github.com/henrywork059/AiTL/actions/runs/45755422084) passed. Standard CI executed three Python lifecycle tests on the actual existing movement helper with fixed phase inputs: both directions, WALK entry, CLEAR continuation, non-WALK curb holds, 30 vs 90 reference pixels/s slow/normal fixtures and seeded reentry. TypeScript motion tests passed for stationary/slow displacement, repeated frames, pause/resume, reentry both directions, reset/source/density/gap and removal; sample independence also asserted. Actual WebGL trial directly asserts persistent pedestrian group reference identity, interpolated position, limb rotation, paused gait freeze and removal; drawing, top view, context loss and cleanup passed. React integration confirms opt-in, source change, editor/overlay fallback, retry and rollback. Both blocking audits reported zero known npm vulnerabilities at execution time. Downloaded [artifact 15087790604](https://github.com/henrywork059/AiTL/actions/runs/45755422084/artifacts/15087790604); SHA-256 31048dfc19e162a4076c5031a3c1f74901f73dd67bba2a91ad2572f953358f35 matches metadata; 1000×650 actual screenshot inspected, three figures (two pavements, one crossing), four vehicles, markings and signals visible, MESH_RENDERER_PASS. Screenshot is a deliberately staged rendering fixture, not proof of safe concurrent movements. Package/lock blobs match b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence: executed synthetic tests, not field data.

See [Patch 0_5_70](PATCH_0_5_70.md). Exact release CI and owner PASS pending.

---

# V0569 — Persistent vehicle meshes and bounded motion interpolation

Candidate `0_5_69`; previous `0_5_68`; accepted baseline `0_5_0`; Update 24 / S03. Owner PASS pending.

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use the synthetic preview, confirm legacy default, disable visible overlays if needed, select Three.js preview; observe all vehicle classes, both travel directions, stop/reentry, pause/resume and density changes. Switch camera A–D, orbit/Top/Zoom/Reset and resize. Select Legacy view; open the editor, drag/save/reopen a vertex and check unchanged coordinates; enable overlays and verify automatic fallback. Confirm no physical camera or signal output changes. Owner alone confirms PASS.

Application revision `8abcac5e874f488604bf084983fbe6976f8159d0`: [standard CI 45753991244](https://github.com/henrywork059/AiTL/actions/runs/45753991244) and [renderer CI 45753991208](https://github.com/henrywork059/AiTL/actions/runs/45753991208) passed. Actual deterministic motion regression covers midpoint/end, interrupted interpolation, duplicate snapshot, synthetic turning and mirrors, east/west reentry, pause/resume, reset, density/source change, removal and frame-sampling independence. Browser trial checks four mesh variants, increasing heights, bus detail and shape signature; actual WebGL drawing, pixel variation, top view, context-loss, repeated disposal, and production React editor/overlay fallback, source switch, retry/rollback and cleanup passed. Persistent group reuse/removal verified by source inspection; the browser test does not directly assert group reference identity across updates. Both blocking npm audits reported zero known vulnerabilities at execution time. Downloaded [artifact 15086527983](https://github.com/henrywork059/AiTL/actions/runs/45753991208/artifacts/15086527983); archive SHA-256 f9211ce575f67c11158eb610d188ee899076c7319293fe0aa3b59a802983e110 matched metadata. Actual 1000×650 screenshot visually inspected: four distinguishable orange vehicles, crossing, markings and signals, MESH_RENDERER_PASS. Package and lock blob hashes match prior validated manifests b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence class: executed synthetic fixtures and browser trials; not field data.

See [Patch 0_5_69](PATCH_0_5_69.md). Exact release CI and owner PASS pending.

---

# V0568 — Opt-in Three.js road renderer

Candidate `0_5_68`; previous `0_5_67`; accepted baseline `0_5_0`; Update 23 / S03. Owner PASS pending.

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use synthetic preview; confirm legacy default, hide visible overlays if necessary, select Three.js preview, test orbit/Top/Zoom/Reset, A–D and resize; select Legacy view, reopen the editor, drag/save/reopen a vertex, check unchanged reference coordinates, re-enable overlays and verify fallback. Confirm physical camera and signal output unchanged. Owner alone confirms PASS.

Application revision `6380561a6038d0dc3ee85a4bd7cf2bd1a0dc705f`: [standard CI 45740124107](https://github.com/henrywork059/AiTL/actions/runs/45740124107) and [renderer CI 45740124021](https://github.com/henrywork059/AiTL/actions/runs/45740124021) passed. Geometry fixtures cover four mirrored views; isolated WebGL draw/pixel/top-view/context-loss/disposal and React integration tests passed (actual component with mocked read-only synthetic scene: default legacy, opt-in, source A→B, top view, editor/region-overlay fallback, loss/retry, rollback and cleanup). Both audits reported zero known npm vulnerabilities at execution time. Exact generated manifest and lock blobs b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b; eight new lock entries, existing non-root entries unchanged. Earlier 23c screenshot inspected; [23d artifact 15080298917](https://github.com/henrywork059/AiTL/actions/runs/45740124021/artifacts/15080298917) retains screenshot/manifests; no fresh manual inspection claimed. Evidence: executed synthetic browser tests, not field data.

See [Patch 0_5_68](PATCH_0_5_68.md). Exact release CI and owner PASS pending.

---

# V0567 — Optional SUMO shadow integration

Candidate `0_5_67`; previous `0_5_66`; accepted baseline `0_5_0`; Update 22 / S02. Owner PASS pending.

```powershell
# From repository root; normal owner acceptance uses legacy default.
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Optional shadow verification is a separate controlled exercise, not required for default acceptance. Use an existing trusted Windows x64 Python 3.10/3.11 backend virtual environment after the default runner has initialized it. Stop the running PC Studio backend first. From `AI_Traffic_Light/apps/pc-studio/backend`:

```powershell
& .\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --only-binary=:all: --no-deps --require-hashes -r requirements-sumo-shadow-win-x64.txt
if ($LASTEXITCODE -ne 0) { throw 'Optional SUMO installation failed' }
& .\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
$env:MESH_SUMO_SHADOW = '1'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In the existing frontend, enable simulation, observe the diagnostics at `http://127.0.0.1:8000/api/camera/simulation/shadow`, pause/resume, change density and switch off simulation. Verify the legacy scene is unchanged, the shadow advances separately and resets/clears on stop. Stop the optional backend with Ctrl+C; remove `Env:MESH_SUMO_SHADOW` and restart the normal runner to roll back. Do not enable with live-road hardware or expose the optional service to untrusted networks.

Executed release-gate evidence for application revision `fc3508e52adf460a19fe32b74c8324903d90e35f`: [standard CI 45737386040](https://github.com/henrywork059/AiTL/actions/runs/45737386040) passed compilation, structure, offline regressions (including camera integration and runtime), frontend regressions/typecheck/build and blocking npm audit (0 reported vulnerabilities). [Native CI 45737386082](https://github.com/henrywork059/AiTL/actions/runs/45737386082), Windows x64 Python 3.10.11, passed exact hash-pinned installation, pip check, version-specific PyPI advisory checks (zero active advisories for all five packages), adapter/child process/runtime tests, native reference and controlled simulation. The earlier [Python 3.11 native CI 45736465611](https://github.com/henrywork059/AiTL/actions/runs/45736465611) also passed the reference trial. Both native-plan reference runs reproduced the TraCI digest `34c24376cf005cdb3d5f9ab0b4aab822847970f49b380fdf139fb0426ee76097` exactly. Each controlled run (seed 42, 300 s, 0.2 s step, 1500 ticks) observed 24 agents, completed 12/12 vehicles and 12/12 pedestrians, and produced digest `28a85055d3ef862650da3fce4aef5e8018f4eb37a9e0f2d3bb017eecf4e7c902`. Observed states were `rrrrrGrrrrrrrGrrrrrr`, `rrrrrrrrrrrrrrrrGGGG`, and `rrrrrrrrrrrrrrrrrrrr`; no simultaneous vehicle/pedestrian grants in the tested fixture. Asynchronous runtime and native failure recovery passed. [Retained artifact 15080205533](https://github.com/henrywork059/AiTL/actions/runs/45737386082/artifacts/15080205533), expires 10 December 2026 09:42 HKT. Results verified from CI logs; newest raw artifact not independently re-inspected in this release step.

See [Patch 0_5_67](PATCH_0_5_67.md). Exact release commit CI and owner PASS pending.

---

# V0566 — Frontend dependency security remediation

Candidate `0_5_66`; previous `0_5_65`; accepted baseline `0_5_0`; security prerequisite 21b (not a numbered roadmap completion).

```powershell
# From AI_Traffic_Light/apps/pc-studio/frontend
npm ci
npm audit --audit-level=high --json
npm run test:data-access
npm run typecheck
npm run build
```

Executed evidence: [dependency trial 45630253510](https://github.com/henrywork059/AiTL/actions/runs/45630253510), job 139261197887, completed successfully on Windows with Node 22. Exact-version resolution, regenerated lock, npm ci, npm ls/version assertions, blocking audit, frontend data-access tests, typecheck and build passed. Audit JSON reported zero known vulnerabilities at run time (0 high, 0 critical, 0 total). Reassembled both complete UTF-8 manifests from ordered base64 log chunks (1 and 39, respectively), parsed JSON and reviewed dependency diff and registry/integrity fields before staging. Previous unchanged application standard CI [45630253344](https://github.com/henrywork059/AiTL/actions/runs/45630253344) passed with non-blocking audit on the old lock. New committed candidate CI and owner PASS remain pending; no local full checkout due to DNS.

See [Patch 0_5_66](PATCH_0_5_66.md).

---

# V0565 — Fixed-step legacy simulator adapter

Candidate `0_5_65`; previous `0_5_64`; accepted baseline `0_5_0`; Update 21 / S02.

```powershell
# From AI_Traffic_Light
python scripts/test_v0565_simulation_adapter.py
python scripts/test_camera_frame_service.py
python scripts/test_camera_simulation_api.py
python scripts/test_v0515_3d_simulation.py
```

Executed three isolated unittest cases against the exact new adapter on Python 3.13.5: different poll partitions (20 identical fixed steps over one second), pause/resume with preserved remainder, capped catch-up, backwards monotonic guard, reset and invalid durations. Both isolated Python files compiled. Verified Git blob hashes: adapter bed0c3ef779d3f4d3a63df10449a0ff940881904; regression 18a9deeff86bc1fb4fd688921cca114e85eca5d6. A fourth regression exercises actual legacy camera agents with injected clock/seed and fixed synthetic phase; it has not been executed locally. Full checkout unavailable due to GitHub DNS failure, so camera integration, old API/signal regressions and current full CI pending. Previous [0_5_64 full CI](https://github.com/henrywork059/AiTL/actions/runs/45619974507) passed. Owner PASS pending.

Security gate: previous CI audit JSON (run 45619974507, 25 Nov 2026) identified two high-severity vulnerable packages: locked source-map-js 1.2.1 ([GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), patched range starts at 1.2.2) and direct Vite 8.2.1 ([GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm), audit suggested Vite 8.3.8; additional lower-severity Vite advisories listed in the CI log). The audit step is non-blocking, exited 1, and is not a security PASS. No dependency changes here; package remediation requires regenerated lockfile and fresh audit/build/test evidence. Restrict prototype development server to trusted local access; do not expose it to untrusted networks or open untrusted projects/source maps. Security remediation takes priority before new dependencies; real SUMO smoke and security gates remain blockers for Update 22.

See [Patch 0_5_65](PATCH_0_5_65.md).

---

# V0564 — Simulation engine evaluation foundation

Candidate `0_5_64`; previous `0_5_63`; accepted baseline `0_5_0`; Update 20 / S01.

```powershell
# From AI_Traffic_Light, no optional dependencies needed for these checks
python scripts/test_v0564_engine_evaluation.py
python -m py_compile scripts/evaluate_simulation_engine.py scripts/test_v0564_engine_evaluation.py
# Optional: only after vetted SUMO installation, with sumo and netconvert on PATH
python scripts/evaluate_simulation_engine.py --output "$env:TEMP\mesh-sumo-evaluation.json"
```

Actual local evidence (25 November 2026): Python 3.13.5, Linux x86_64; three offline unittest cases passed and both Python files compiled. The real harness ran and returned exit 2 / blocked with zero trials because sumo and netconvert were absent from PATH; no TraCI, libsumo or CityFlow package installed. GitHub checkout DNS failed; no full local checkout or renderer test. Exact staged Git blobs: harness 448f17187d9c7afcf216438e0915de92f7cb3411, test 81c629182523bd8675d2a5921f0c028d9c754925. Prior full CI passed ([45601046778](https://github.com/henrywork059/AiTL/actions/runs/45601046778)); new CI and owner PASS pending. No measured third-party engine performance or physical validation.

Engine choice is conditional, not adoption. Before shadow integration, run the optional smoke scenario on a pinned Windows SUMO distribution and validate pedestrian path/crossing geometry, both traces and error handling. Before dependency adoption, inspect existing npm high-severity findings and proposed dependency tree, verify licenses and versions, and document remediation or explicitly accepted residual risk. Compare matched traffic and render workloads; retain rollback, independent safety rules and no physical actuation. No throughput, CPU/RAM, GPU, latency or safety superiority has been demonstrated. Update 21 can proceed with the existing simulator adapter and deterministic clock without new dependencies; Update 22 must wait for engine and security gates.

See [Patch 0_5_64](PATCH_0_5_64.md) and [engine evaluation](SIMULATION_ENGINE_EVALUATION.md).

---

# V0563 — Centralized frontend polling and cancellation

Candidate `0_5_63`; previous `0_5_62`; accepted baseline `0_5_0`; Update 19 / A04.

From `AI_Traffic_Light` (frontend dependencies installed):

```powershell
python scripts/test_frontend_polling_structure.py
Push-Location apps/pc-studio/frontend
npm run test:data-access
npm run typecheck
npm run build
Pop-Location
```

Executed the actual pollingScope and apiClient modules with a mocked Node 22 fetch/response test and strict isolated TypeScript compilation, both passed. Git blob hashes for these modules and the test must match the locally tested files. Full checkout unavailable (GitHub DNS failure reproduced); integrated React typecheck/build and full CI pending. Previous 0_5_62 full CI passed ([run 45579569473](https://github.com/henrywork059/AiTL/actions/runs/45579569473)). The new npm test is wired into CI after npm ci. No owner PASS.

Correction 19a (same candidate): [initial CI run 45580743596](https://github.com/henrywork059/AiTL/actions/runs/45580743596) passed compile/structure and reached the historical V059 regression, which incorrectly expected the pre-cancellation `fetchCameraInference(sourceId)` call. Updated the regression to verify signal forwarding, scope retirement, camera/model restart key and the guard before state publication; retained existing settings, model registry and region checks. No runtime source changed. Reproduced the obsolete predicate and checked all 11 current grouped frontend predicates directly against the actual parent source (12 checks including reproduction); these are source checks, not execution of the full Python test. Direct Git checkout remains blocked by DNS resolution. Corrective full CI, frontend runtime test, TypeScript/build and owner PASS pending. Do not advance until corrective CI passes.

Correction 19b (same candidate): [CI run 45591924618](https://github.com/henrywork059/AiTL/actions/runs/45591924618) passed compile, structure, full offline regressions (including corrected V059) and npm ci. The new frontend data-access harness failed before its assertions at `ts.ModuleKind.CommonJS`: the lockfile specifies native TypeScript 7.0.2, which does not provide the old JavaScript compiler API. Replace the harness loader with the locked tsc CLI, an isolated temporary CommonJS project (NodeNext), strict compilation of byte-identical source copies and cleanup in finally. All existing behavioral assertions are retained. Executed corrected harness locally with Node 22.16.0 and available TypeScript 5.8.3; passed strict compilation and mocked runtime checks. Verified all five staged Git blob hashes against tested files (test 6c7e3ca009f0e99be0d116ff9f0aae20c345cc38). Windows CI with locked TypeScript 7.0.2, integrated typecheck/build and owner PASS remain pending; no runtime or dependency changes. GitHub/npm DNS resolution is unavailable in the local environment. npm ci also reported two high-severity vulnerabilities without package/advisory details: investigate via npm audit before any new dependency adoption; do not assume a forced upgrade is safe. Reference: https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ .

See [Patch 0_5_63](PATCH_0_5_63.md).

---

# V0562 — Source-qualified traffic observations

Candidate `0_5_62`; previous `0_5_61`; accepted baseline `0_5_0`; Update 18 / A03.

From `AI_Traffic_Light`:

```powershell
python scripts/test_v0562_traffic_observations.py
python scripts/test_v0561_tracking_scope.py
python scripts/test_object_tracking_flow.py
python scripts/test_zone_traffic_services.py
python scripts/test_traffic_history_service.py
python scripts/test_junction_network_overview.py
python scripts/test_v0550_signal_stale_fallback.py
```

Locally executed 18 isolated helper cases using stub camera/manager and identity interfaces; compilation passed and Git blob 88909a0b47fc7c427e46609ed430a21278e06c0d matches. Initial isolated test fixture had an incorrect nested retirement token and was corrected before the passing run. Full checkout unavailable due to GitHub DNS failure; new integration regression and full CI pending. Previous CI passed (run 45555018709). Windows/ESP owner PASS pending.

See [Patch 0_5_62](PATCH_0_5_62.md).

---

# V0561 — Scope selected-source tracking by camera and junction

Candidate `0_5_61`; previous `0_5_60`; accepted baseline `0_5_0`; Update 17 / A03.

From `AI_Traffic_Light`:

```powershell
python scripts/test_v0561_tracking_scope.py
python scripts/test_object_tracking_flow.py
python scripts/test_zone_traffic_services.py
python scripts/test_v0547_cached_frame_identity.py
python scripts/test_v0550_signal_stale_fallback.py
```

Locally executed the isolated TrackingContinuity helper: 16 targeted assertions plus a bounded-source loop; compilation passed. The helper's staged blob must match the locally tested hash. Full producer/route/tracker regressions were added but not run locally: GitHub DNS resolution failure reproduced. Previous candidate corrective CI passed ([run 45538583036](https://github.com/henrywork059/AiTL/actions/runs/45538583036)); current CI and Windows/ESP owner acceptance pending. Physical throughput/CPU comparison and lighting/speaker gates remain outstanding.

See [Patch 0_5_61](PATCH_0_5_61.md).

---

# V0560 — Separate ATL1 transport framing from camera lifecycle

Candidate `0_5_60`; previous `0_5_59`; accepted baseline `0_5_0`; Update 16 / A04.

From `AI_Traffic_Light`:

```powershell
python scripts/test_v0310_camera_pipeline.py
python scripts/test_v0560_tcp_transport.py
python scripts/test_remote_camera_session.py
python scripts/test_remote_camera_multi.py
python scripts/test_remote_camera_control_resilience.py
python scripts/test_v0544_tcp_read_cancellation.py
python scripts/test_v0545_tcp_open_cancellation.py
python scripts/test_v0546_worker_retirement.py
python scripts/test_v0552_camera_transport_diagnostics.py
```

Three isolated regression groups passed (fragmented framing, socket shutdown, malformed/truncated packets); isolated Python compilation passed. The local test uses the existing 8 MiB frame-size constant in an isolated stub; full checkout could not be cloned because GitHub DNS resolution failed. Full candidate CI, actual ESP throughput/CPU comparison and Windows/ESP owner PASS remain pending. No performance improvement claimed. Previous 0_5_59 CI passed ([run 45518551845](https://github.com/henrywork059/AiTL/actions/runs/45518551845)).

Correction 16a (same candidate): [initial CI run 45531504572](https://github.com/henrywork059/AiTL/actions/runs/45531504572) passed compilation and structure, but stopped at `test_v0310_camera_pipeline.py` because the historical static test still expected `FRAME_MAGIC` in `remote_camera.py`. Updated it to check the extracted codec owner, header format, session import and decoder call; retained the firmware and session assertions. Extended the new transport regression to check compatibility-import object identity. No runtime source or wire protocol change. Reproduced the old predicate failure and checked all 43 corrected static predicates against eight actual files fetched from the parent commit. These checks are a direct source inspection, not execution of the Python scripts. A full local checkout remains unavailable (GitHub DNS resolution failure confirmed); new Python regression execution, full CI and owner/physical validation remain pending.

See [Patch 0_5_60](PATCH_0_5_60.md).

---

# V0559 — Unified camera observation identity

Candidate `0_5_59`; previous `0_5_58`; accepted baseline `0_5_0`; Update 15 / A02.

Run from `AI_Traffic_Light`:

```powershell
python scripts/test_v0559_observation_identity.py
python scripts/test_v0547_cached_frame_identity.py
python scripts/test_v0548_observation_invalidation.py
python scripts/test_v0550_signal_stale_fallback.py
```

Seven isolated contract assertions and isolated module compilation passed locally. New producer integration regression and existing freshness/safety regressions require full CI; local checkout unavailable (GitHub DNS blocked). Previous candidate CI passed (run 45517777657). Owner Windows/ESP PASS pending; baseline remains `0_5_0`.

See [Patch 0_5_59](PATCH_0_5_59.md).

---

# V0558 — Synthetic speaker regression

Candidate `0_5_58`; previous `0_5_57`; accepted baseline `0_5_0`; roadmap Update 14 / H07.

From `AI_Traffic_Light`:

```powershell
python scripts/test_v0558_bench_speaker.py
python scripts/test_v0557_bench_lighting.py
python scripts/run_offline_tests.py --focused test_v0558_bench_speaker.py test_v0557_bench_lighting.py test_v0556_bench_output.py
python scripts/check_structure.py
```

Seven speaker and six lighting regressions passed locally (13 tests); isolated Python compilation passed. Previous candidate CI passed ([run 45515165289](https://github.com/henrywork059/AiTL/actions/runs/45515165289)). Current full CI and owner acceptance pending. The focused speaker and lighting tests and isolated compilation ran locally, not the full checkout or frontend build. No audio or hardware connection is required. Physical speaker integration is BLOCKED: hardware model, amplifier/driver, electrical specifications, acoustic limits, independent hardware fail-safe and controlled-bench authorization remain unconfirmed or unavailable. No acoustic or physical safety validation was performed. Physical lighting also remains blocked. Use the normal owner runner with `-SkipUpdate` from the repository root. See [Patch 0_5_58](PATCH_0_5_58.md).

---

# V0557 — Synthetic lighting regression

Candidate `0_5_57`; previous `0_5_56`; accepted baseline `0_5_0`; roadmap Update 13 / H07.

From `AI_Traffic_Light`:

```powershell
python scripts/test_v0557_bench_lighting.py
python scripts/run_offline_tests.py --focused test_v0557_bench_lighting.py test_v0556_bench_output.py test_v0554_device_capabilities.py
python scripts/check_structure.py
```

Six focused deterministic tests and compilation of the isolated sources passed locally; prior candidate CI passed ([run 45434249530](https://github.com/henrywork059/AiTL/actions/runs/45434249530)). Current full CI and owner acceptance pending. Only the new focused regression and isolated compilation ran locally. Do not attach hardware. Physical integration is BLOCKED: lighting model, voltage/current requirements, driver/electrical interface and controlled-bench authorization remain unconfirmed; an independent hardware fail-safe is not implemented. No physical testing or electrical safety validation was performed. Follow the normal owner runner from the repository root with `-SkipUpdate`. See [Patch 0_5_57](PATCH_0_5_57.md).

---

# V0556 — Fake-only bench output regression

Candidate `0_5_56`; previous `0_5_55`; baseline `0_5_0`.

From `AI_Traffic_Light`:

```powershell
python scripts/test_v0556_bench_output.py
python scripts/run_offline_tests.py --focused test_v0556_bench_output.py test_v0554_device_capabilities.py test_v0554_device_registry.py
python scripts/check_structure.py
```

Eight deterministic fake-adapter tests passed locally, including timeout/ack faults, duration bounds, unsupported commands, unauthorized arming, overlap, disconnect, off and monotonic expiry. No electrical or hardware test is part of this update. Watchdog tick and active-state reads enforce a fake lease, not an autonomous physical watchdog. Use the normal owner runner with `-SkipUpdate` from the repository root; no physical actuation.

---

# V0555 — Device setup and connection workflow

Candidate `0_5_55`; previous `0_5_54`; accepted baseline `0_5_0`.

Focused tests from `AI_Traffic_Light`:

```powershell
python scripts/run_offline_tests.py --focused test_v0555_camera_setup.py test_camera_settings_page_structure.py test_remote_camera_control_resilience.py test_remote_camera_multi.py test_v0554_device_registry.py test_v0554_device_capabilities.py
python scripts/check_structure.py
```

The new regression exercises fake ESP status failures, explicit retry, invalid settings and IP, persistence, selection changes during refresh and removal. UI structure guards verify validation, action epoch, source-identity guards and fresh-frame preview gating. Full suite/typecheck/build via GitHub CI, actual Windows application and ESP checks remain separate.

From repo root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Use one or two authorized bench ESPs: confirm invalid input rejection; unplug, connect and retry after restoring network; verify distinct camera states, no stale preview, stop before reconnect, profile reload and no unexpected output. Do not equate CI with owner PASS.

---

# V0554 — Device capability contract

Candidate `0_5_54`, previous `0_5_53`, accepted baseline `0_5_0`, roadmap Update 10 / H06.

Run these from `AI_Traffic_Light`:

```powershell
python scripts/run_offline_tests.py --focused test_v0554_device_capabilities.py test_v0554_device_registry.py test_remote_camera_multi.py test_remote_camera_session.py test_v0552_camera_transport_diagnostics.py test_v0525_camera_diagnostics.py
python scripts/check_structure.py
```

Pure isolated contract test passed locally: 3/3 pytest functions, direct execution and Python compilation. CI run 45424883577 failed because the older V0525 diagnostics fixture omitted the V0548 source-lifetime token. The fixture was corrected without changing the production freshness guard; [CI run 45425380717](https://github.com/henrywork059/AiTL/actions/runs/45425380717) subsequently passed full offline regression, structure, TypeScript typecheck and frontend build at code commit 1840f9bc. The V0554 registry round-trip regression also passed in that CI run. Owner Windows/ESP acceptance remains pending. The integration test `test_v0554_device_registry.py` was added but not executed locally because the full source checkout could not be retrieved via DNS; no real ESP hardware was used. Verify legacy V1 profile reload, new contracts on all physical/simulation sources, source matching after selection, unavailable outputs, no unexpected writes/commands, and stale/stream state.

From repository root, owner acceptance:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Only explicit owner PASS may update `passed_baseline`. CI/frontend/Windows full run and ESP recovery must still be checked.

---

# V0553 — Camera endurance evidence

Candidate `0_5_53`, previous `0_5_52`, baseline `0_5_0`.

Focused offline test (zero arguments):

```powershell
cd .\AI_Traffic_Light
python scripts/run_offline_tests.py --focused test_v0553_camera_endurance.py test_v0552_camera_transport_diagnostics.py test_remote_camera_session.py test_remote_camera_multi.py
```

The new synthetic fixture independently verifies 2 saved cameras, reconnect timing, counter resets, stale frames, CSV and JSON schema and privacy; it does **not** demonstrate real ESP frame rate or weak-network recovery. Locally executed standalone regression: PASS; pytest: 3 passed; recorder/test compile: PASS. Full repository suite and structural checker not run in agent environment.

To measure real camera transport while PC Studio and the ESP(s) are already streaming, execute from `AI_Traffic_Light`:

```powershell
python scripts/camera_endurance_benchmark.py --duration-seconds 600 --sample-seconds 1 --environment "Record board, firmware, power, AP, Wi-Fi distance and conditions"
```

Default output: `$HOME\MESH_camera_endurance\<UTC-run-id>\samples.csv` and `summary.json`. Optional `--source-id esp32_cam_01`, `--backend-pid <actual-backend-pid>` with optional `psutil`, and `--output-dir <new-directory>`. Repeated source IDs select multiple cameras. Record actual firmware/version and use Git HEAD in summary (null if unavailable); review missing values before reporting results. CPU is percent of one logical core and memory is backend-process MiB; values are null without process access.

For owner full acceptance, from repo root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Full offline suite, frontend build, UI/end-to-end checks and actual ESP/wireless-duration experiments remain outstanding; no owner PASS.

---

# V0552 — Camera transport diagnostics

Candidate `0_5_52`, previous `0_5_51`, baseline `0_5_0`, Update 08 / H05.

Focused test: `python scripts/run_offline_tests.py --focused test_v0552_camera_transport_diagnostics.py test_remote_camera_session.py test_remote_camera_pull.py test_v0544_tcp_read_cancellation.py test_v0545_tcp_open_cancellation.py test_v0546_worker_retirement.py test_v0547_camera_frame_identity.py test_v0548_camera_observation_invalidation.py`. If a named prior test does not exist, use actual discovered names rather than interpreting a missing test as success. Then run full suite, structure guard, frontend build and Windows runner.

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify repeated/gap/reset/wrap sequences, monotonically measured intervals, original cache timestamp, disconnected FPS, two cameras, worker retirement and reconnect. Real ESP frame throughput, weak-Wi-Fi and reboot recovery require separate hardware evidence. Local Git checkout failed due DNS resolution; full repo/Windows/ESP/CI validation was not performed here. No owner PASS.

---

# V0551 — Emergency evidence and virtual network clearance

Candidate `0_5_51`, previous `0_5_50`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Run `python scripts/run_offline_tests.py --focused test_v0551_emergency_interlocks.py test_v0512_emergency_corridor.py test_v0514_network_conflicts.py test_v0519_emergency_evidence.py test_v0521_ambulance_single_source.py test_v0522_network_disconnect.py` and the full runner.

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Local Python 3.13.5: original coordinator source matched GitHub FNV-1a f9c8e054; reproduced two defects (compatible grant erased clearance and standalone invalid lamp passed through). Patched coordinator whole module df44e28b and new evidence helper 6152a7b8 executed locally: six targeted coordinator checks plus 64 configured movement/conflict pairs and seven emergency evidence cases all passed. No service integration or physical testing claimed. Added test_v0551_emergency_interlocks.py including pending-priority withdrawal integration cases; full regression not executed. Direct GitHub ls-remote failed DNS resolution; CI and owner Windows/ESP PASS pending.

---

# V0550 — Stale-input virtual signal fallback

Candidate `0_5_50`, previous `0_5_49`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Run `python scripts/run_offline_tests.py --focused test_v0550_signal_stale_fallback.py test_signal_rules_service.py test_signal_scenarios.py test_v0512_camera_crosswalk.py test_select_changed_tests.py` and then the full runner. Verify stale/missing inputs, competing scenarios, protected phases, class availability, two-view freshness and emergency interlocks.

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Five defects reproduced with four copied original method blocks matched to GitHub by FNV-1a. Ten patched isolated behavioral checks passed (expired, unavailable, future/missing, replay, stale persistence, unavailable persistence, unpolled gap, unknown class, five-second cap, explicit Test mode). Patched block hashes: observe/clear/freshness 6d63a0c9, condition value 59d80e9b, candidate evaluation 1157b7a2, observation values 9965254b. Test harness injected clock, constructor, memory and scenario-match dependencies; this is not full controller or integration testing. The repository regression includes the real protected phase sequence and fused-view age checks; not executed locally. The changed-test selector regression also executed successfully, with source hashes 75004545 and 1c8e6d9f; compileall of the local harness and selector files passed. Direct clone still fails DNS; full CI/Windows/ESP owner PASS pending.

---

# V0549 — Reproducible offline regression execution

Candidate `0_5_49`, previous `0_5_48`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

From `AI_Traffic_Light/` using a Python environment with backend requirements installed:

```text
python scripts/run_offline_tests.py --list
python scripts/run_offline_tests.py
```

Use `python scripts/run_offline_tests.py --focused test_v0548_observation_invalidation.py` for a specific offline regression. On Windows, use the backend venv interpreter if it is not active.

Fresh Windows backend setup: `scripts/setup_backend_windows.ps1` (Python 3.11 via py launcher); existing venv retained. Then from repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Executed original camera filename selection expression with five fixture names: only 1/5 selected, four numbered lifecycle regressions omitted. Executed patched test_offline_test_discovery.py and test_select_changed_tests.py on local Python 3.13.5: both passed, including actual child process execution/fail-fast exit 7; compileall of the four Python files passed. FNV-1a source checks: runner 8d76d515, runner test 351b1672, selector bd6c3d59, selector test 2fb1332b. Direct GitHub ls-remote failed DNS resolution; PowerShell not installed locally. Full repository checkout, Windows runner, CI and hardware acceptance remain pending.

---

# V0548 — Invalidate disconnected camera observations

Candidate `0_5_48`, previous `0_5_47`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Run `python scripts/test_v0548_observation_invalidation.py`, `python scripts/test_remote_camera_multi.py`, `python scripts/test_v0527_late_inference_shutdown.py`, V0544–V0547 and full runner.

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify stop/disconnect/restart, two independent cameras, mode round trips and AI preview. Executed isolated Python reproduction using the retrieved original stop/disconnect and inference-snapshot methods: both operations left the cached image available (2/2 defects reproduced). Patched isolated execution passed 9/9 behavioral checks: stop/neighbour isolation, stale API result suppression, stopped callback, cancelled worker after restart, new delivery and slow current observation, simulation round trip, disconnect, old device generation, and inference completion/virtual snapshot filtering. All 12 copied patched method bodies matched staged source by FNV-1a checksum. Camera/session/clock/model/controller dependencies were injected; this is not a full-module test. Direct GitHub clone failed DNS resolution. Repository regressions added; full CI and owner Windows/ESP acceptance pending.

---

# V0547 — Preserve ESP cached-frame identity

Candidate `0_5_47`, previous `0_5_46`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Run `python scripts/test_v0547_cached_frame_identity.py`, `python scripts/test_remote_camera_multi.py`, V0544–V0546, structure, full offline regressions and frontend typecheck/build.

From repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify rapid A/B/A selection, fresh/stale cache behavior, exact source/frame identity, simulation return and normal streaming. Reproduced against the original hash-matched promotion method with an injected receiver: original timestamp 1000 became 1100 and two promotions allocated IDs 1 and 2. Patched isolated method execution passed 9/9 behavioral checks using three FNV-1a-matched source blocks (camera upload methods ca8e8669, manager ingest/promotion 29058cfc, inference snapshot a7bfb222), injected dependencies and real JPEG fixtures: background isolation, preserved time/ID, A/B/A replay, distinct same-ms packets, stale rejection, simulation ownership transition, ordinary upload, retired generation and invalid image rejection. This is not full-module regression execution; image validation and simulation were injected. Direct clone failed DNS resolution; repository regression, full CI and owner Windows/ESP validation pending.

---

# V0546 — ESP worker retirement and recovery

Candidate `0_5_46`, previous `0_5_45`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap Update 02 / H02. Run `python scripts/test_v0546_worker_retirement.py`, `python scripts/test_v0545_tcp_open_cancellation.py`, `python scripts/test_v0544_tcp_read_cancellation.py`, `python scripts/test_remote_camera_pull.py`, `python scripts/test_remote_camera_session.py`, structure, offline regressions and frontend typecheck/build.

From repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -SkipUpdate
```

Verify repeated stream restart, recovery after ESP reboot or Wi-Fi loss, simulation entry/exit, no stale disconnected status and normal frame delivery. Original isolated method probes reproduced stale join status and stale recovery publication/rearm, and confirmed failure recording lacks a worker guard. The patched methods passed 11/11 isolated behavioral checks with injected dependencies (four transport cases, one join, five recovery cases and one late frame sink); the copied method blocks were hash-matched to the staged source. Direct clone blocked by DNS. Full-module tests, CI for this candidate and owner Windows/ESP acceptance are not yet verified.

---

# V0545 — ESP TCP socket-open cancellation

Candidate `0_5_45`, previous `0_5_44`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap Update 01 / H02. Run `python scripts/test_v0545_tcp_open_cancellation.py`, `python scripts/test_v0544_tcp_read_cancellation.py`, `python scripts/test_remote_camera_pull.py`, `python scripts/test_remote_camera_session.py`, structure validation, full offline regressions and frontend typecheck/build.

From the repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify normal preview, stop during connection, repeated stop/start, simulation entry/exit and camera reconnection. Isolated execution of the exact retrieved `_run` method with injected opener, consumer and operating state: original 2/5, patched 5/5 (stop, restart, simulation switch, normal open, reconnect). Direct clone unavailable because DNS resolution failed; full-module regression and repository CI were not run locally. Owner Windows/ESP PASS pending.

---

# V0544 — ESP TCP post-read cancellation boundary

Candidate `0_5_44`, previous `0_5_43`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Run `python scripts/test_v0544_tcp_read_cancellation.py`, `python scripts/test_remote_camera_pull.py`, `python scripts/test_remote_camera_session.py`, structure validation, offline regressions and frontend typecheck/build. The focused regression verifies stop, simulation switch, normal packet, normal EOF, stop during EOF and simulation switch during EOF. No physical signals are driven.

From the repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -SkipUpdate
```

Confirm normal preview, repeated stop/start, simulation entry/exit and resumed physical preview. Explicit owner PASS required.

---

# V0543 — Fragmented upload memory regression

Candidate `0_5_43`, previous `0_5_42`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Focused tests: `python scripts/test_v0540_camera_upload_stream_limit.py`, `python scripts/test_v0541_camera_upload_integrity.py`, and `python scripts/test_remote_camera_pull.py`. The V0540 test now submits 4,098 streamed chunks including an empty chunk, verifies assembled bytes, and retains exact-boundary and immediate-oversize rejection checks.

On Windows, from repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Run structure validation, all offline regressions, frontend typecheck/build and browser checks. Verify camera preview/uploads, existing ESP TCP session and 3D scene. Explicit owner PASS required.

---

# V0542 — HTTP-versus-ESP camera ingestion boundary

Candidate `0_5_42`, previous `0_5_41`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Run `python scripts/test_v0541_camera_upload_integrity.py`, `python scripts/test_v0540_camera_upload_stream_limit.py`, `python scripts/test_remote_camera_pull.py`, `python scripts/test_remote_camera_session.py` and existing camera service/API tests. The image-validation regression now verifies HTTP strict decode and TCP fast path separately. Run full offline tests, structure and frontend typecheck/build.

Windows owner validation from the repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Confirm large/malformed HTTP uploads reject correctly, valid ESP TCP preview remains responsive, no physical signals are driven, and 3D simulation/editor remain unchanged. Explicit owner PASS remains required.

---

# V0541 — Upload validity and frame preservation

Candidate `0_5_41`, previous `0_5_40`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Run `python scripts/test_v0541_camera_upload_integrity.py`, `python scripts/test_v0540_camera_upload_stream_limit.py`, `python scripts/test_camera_frame_service.py`, `python scripts/test_camera_simulation_api.py`, structure, offline regressions and frontend typecheck/build.

From the repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Check valid PNG/JPEG uploads and confirm malformed or mismatched images return 422 `CAMERA_FRAME_INVALID` without replacing the last valid frame. Verify simulation, camera preview, 3D views and physical ESP remain unaffected. Explicit owner PASS required.

---

# V0540 — Camera upload memory bound

Candidate `0_5_40`, previous `0_5_39`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Focused regression: `python scripts/test_v0540_camera_upload_stream_limit.py`, verifying chunk order, exact 8 MiB success, 8 MiB + 1 byte rejection, no consumption of later chunks, and no call to image processing on oversized uploads. Verify `test_camera_frame_service.py`, `test_camera_simulation_api.py`, structure, offline suite, frontend typecheck/build.

Windows owner test from the repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Confirm normal PNG/JPEG camera uploads, the existing 413 envelope, live simulation, 3D views and physical ESP preview remain unchanged. Hardware and owner PASS remain separate from CI.

---

# V0539 — 3D keyboard regression compatibility

Candidate `0_5_39`, previous `0_5_38`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Focused test: `python scripts/test_v0523_3d_keyboard.py`; confirm the test checks the exported shared camera-mirror helper and scene wiring while keeping keyboard, zoom and editor-guard checks. Also run `python scripts/test_v0515_3d_simulation.py`, structure, the offline suite, frontend typecheck and build.

From the repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify keyboard orbit/tilt/zoom/Home, edit-mode protection, signal-post positions in all four simulation camera views, and unchanged ESP camera handling. Windows/browser owner PASS remains required.

---

# V0538 — Documentation restoration

Candidate `0_5_38`, previous `0_5_37`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Documentation-only correction to restore the full changelog and local-testing guide. The `0_5_37` mirrored signal-post code remains. For runtime validation, run the Windows owner command below and inspect all four views. Owner PASS is still required.

---

# V0537 — Mirrored 3D signal post fix

Candidate `0_5_37`, previous `0_5_36`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Focused regression: `python scripts/test_v0515_3d_simulation.py` verifies canonical, vertical, horizontal and combined source transforms and that both signal posts use the transform. Also run frontend typecheck/build, structure and offline regressions. Windows owner validation: `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`; check all four 3D views and confirm PASS. The patch does not modify live signal policy, source images, region editing or physical camera handling.

---

# V0536 — Simulation layout test update

Candidate `0_5_36`, previous `0_5_35`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Focus: `python scripts/test_simulation_frame_layout.py`, `python scripts/test_v0515_3d_simulation.py`, `python scripts/test_v0418_camera_region_ui.py`, plus full offline regressions, structure, frontend typecheck/build.

From the repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify distinct car/SUV/van/bus models, improved pedestrians, seamless reentry, intact overlays/region editing/physical cameras. Owner PASS required.

---

# V0535 — Varied 3D traffic and pedestrian reentry

Candidate `0_5_35`, previous `0_5_34`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

Focused regressions: `python scripts/test_v0515_3d_simulation.py` and `python scripts/test_v0418_camera_region_ui.py`. The first checks all vehicle types, 3D styling and pure Node tests for pedestrian/vehicle reentry. Run structure, offline regressions and frontend typecheck/build.

From the repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Validate four vehicle silhouettes, different pedestrian appearances, both walking directions and smooth reentry after leaving either edge. Confirm pause/resume, orbit/zoom, 2D capture/regions, green/clearance safety and ESP camera pages are unaffected. Explicit owner PASS required.

---

# V0534 — 3D agents and reentry validation

Candidate \`0_5_34\`, previous \`0_5_33\`, accepted baseline \`0_5_0\`, branch \`feature/interactive-3d-simulation\`.

Run `python scripts/test_v0515_3d_simulation.py` for the existing simulator/3D integration plus six pure Node reentry assertions. Execute structure checks, offline regressions, frontend typecheck/build and full candidate CI.

From the repository root on Windows:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Check all four 3D cameras, top and perspective views, pause/resume, signal behavior, and that cars disappear off-screen then reappear without crossing the road backwards. Verify overlays/region editing, captures and physical camera views. Owner PASS required.

---

# V0533 — Correct conditional simulation toggle regression

Candidate `0_5_33`, previous `0_5_32`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

The previously added `test_v0532_hallmark_shell.py` now asserts the original `showSimulationTools && activePage === "simulation_lab"` condition. Runtime code is untouched. Re-run that regression, full offline suite, frontend typecheck/build and structure guard.

From the repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify brand panel remains inert, labeled button changes visibility with keyboard/mouse, and hiding from Simulation Experiments returns to Dashboard. Explicit Windows acceptance required.

---

# V0532 — Hallmark sidebar design regression

Candidate `0_5_32`, previous `0_5_31`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

**Focus:** `python scripts/test_v0532_hallmark_shell.py` plus existing navigation, palette, responsive and structure regressions. Full candidate CI should also typecheck/build the frontend.

**Windows pull/test from repository root:**

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Confirm brand title no longer triggers simulation visibility; the labeled button does so with pointer and keyboard, including navigating away from the Simulation Experiments page when hidden. Inspect narrow screens and light/dark variants; verify unchanged existing pages, mock/live labels and physical-output restrictions. Explicit owner PASS pending.

---

# V0531 — Camera-region structure regression compatibility

Candidate `0_5_31`, previous `0_5_30`, baseline `0_5_0`, on `feature/interactive-3d-simulation`.

Prior `0_5_30` CI failed in `scripts/test_v0418_camera_region_ui.py` because its source-text assertion still expected the old `_advance_vehicles_locked(step)` and `_advance_pedestrians_locked(step)` calls. This test now verifies the one shared protected phase evaluation in `_advance_simulation_locked` and the phase-aware movement calls; runtime code was not changed.

**Focused regressions:** `python scripts/test_v0418_camera_region_ui.py`, `python scripts/test_camera_frame_service.py`, `python scripts/test_signal_rules_service.py`, `python scripts/test_camera_simulation_api.py`, `python scripts/test_v0515_3d_simulation.py`. Run full candidate CI (compile, structure, all offline regressions, frontend typecheck/build).

**Owner Windows validation** from a clean repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Check stop-line vehicle queues, WALK-only pedestrian entry, yellow/all-red/CLEAR phases, four simulated views and unchanged ESP preview. The default runner updates `main`; it must be invoked with `-SkipUpdate` on this feature branch. Explicit owner PASS required.

---

# V0530 — Shared phase snapshot during simulation movement

Candidate `0_5_30`, previous `0_5_29`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

**Focused tests** (inside `AI_Traffic_Light/`): `python scripts/test_camera_frame_service.py` (one phase evaluation for each of four 50 ms steps, vehicle stop-line, pedestrian curb/WALK, pause/resume and mirrored-frame regressions), `python scripts/test_signal_rules_service.py` (protected phase/scenario behavior), `python scripts/test_camera_simulation_api.py` (request/response semantics), and `python scripts/test_v0515_3d_simulation.py` (3D scene continuity).

**Windows candidate pull/test** from a clean repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Run the full offline regression/structure suite and frontend typecheck/build in candidate CI. Manually verify yellow/all-red/WALK/pedestrian-clear transitions, queued vehicles, pedestrians waiting for WALK, four synthetic 3D views and unchanged ESP camera preview. No quantitative CPU/latency speedup is claimed without a controlled benchmark. Owner PASS required.

---

# V0529 — Simulation mirror-render optimization

Candidate `0_5_29`, previous `0_5_28`, baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

**Focused offline regressions** (from `AI_Traffic_Light/`): `python scripts/test_camera_frame_service.py`, `python scripts/test_camera_simulation_api.py`, `python scripts/test_v0515_3d_simulation.py`. The service test verifies original/mirrored pixel equivalence without PNG decoding and release of the canvas cache on stop.

**Windows feature-branch validation** (from a clean repository root):

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

The default runner pulls `main`, so use `-SkipUpdate` on this branch. Verify all four synthetic views, pause/resume, density/reset behavior, captured images and unchanged real ESP preview. Full candidate CI and explicit owner PASS are required. No benchmarked speedup is claimed.

---

# V0528 — Emergency evidence after camera reconnect

Candidate `0_5_28`, previous `0_5_27`, accepted baseline `0_5_0`. Trust strictly newer source timestamps for emergency-evidence freshness even if a camera reconnect resets its frame counter. A negative reconnect frame clears older ambulance evidence, while equal/older timestamp replays remain rejected. Confirmation still requires two distinct positive observations at least one second apart from the same camera; protected virtual traffic signals and disabled physical outputs are unchanged.

---

Focused: `python scripts/test_v0519_emergency_evidence.py`, `python scripts/test_v0521_ambulance_single_source.py`, `python scripts/test_v0524_camera_source_order.py`, `python scripts/test_v0527_late_inference_shutdown.py`. Run structure, full offline CI, frontend typecheck/build, and verify camera reconnect/negative observation behavior in the Windows simulation; owner PASS pending.

# V0527 — Late inference shutdown guard

Candidate `0_5_27`, previous `0_5_26`, accepted baseline `0_5_0`. Discard late inference results when stop is requested, preventing a model call that finishes after the bounded worker shutdown from repopulating cleared per-camera caches or publishing obsolete Crosswalk observations. The prior duplicate-worker guard, normal inference behavior and disabled physical outputs remain unchanged.

---

Focused: `python scripts/test_v0527_late_inference_shutdown.py`, `python scripts/test_v0526_inference_worker_lifecycle.py`, `python scripts/test_v0525_camera_diagnostics.py`, `python scripts/test_v0524_camera_source_order.py` and `python scripts/test_inference_service.py`. Run structure, full candidate CI, and locally confirm a slow real ESP/model inference stopping cannot resurrect stale camera results; owner PASS pending.

# V0526 — Inference worker shutdown safety

Candidate `0_5_26`, previous `0_5_25`, accepted baseline `0_5_0`. Preserve a live inference worker reference after its 2-second bounded shutdown join expires; subsequent start attempts cannot create parallel inference threads while the prior worker is running. Clear cached observations as before; no changes to inference results, traffic signals or physical outputs.

---

Focused: `python scripts/test_v0526_inference_worker_lifecycle.py`, `python scripts/test_v0525_camera_diagnostics.py`, `python scripts/test_v0524_camera_source_order.py`, `python scripts/test_inference_service.py`; run structure checks, frontend typecheck/build and full offline CI. Verify clean restart with live model/ESP on Windows; owner PASS remains pending.

# V0525 — Per-camera inference diagnostics

Candidate `0_5_25`, previous `0_5_24`, accepted baseline `0_5_0`. Expose measured per-camera inference latency, source frame age and freshness in the existing inference response and Camera AI Preview. Diagnostics are per-source and never fabricated; stale/mismatched-model frames are unavailable for AI overlay. Existing signal decisions and physical-output restrictions are unchanged.

---

Focused: `python scripts/test_v0525_camera_diagnostics.py`, `python scripts/test_inference_service.py`, `python scripts/test_v0524_camera_source_order.py`; frontend `npm run typecheck` and `npm run build`. Validate actual per-camera readings on Windows/ESP.

# V0524 — Multi-camera source freshness

Candidate `0_5_24`, previous `0_5_23`, accepted baseline `0_5_0`. Harden existing per-source background inference: discard repeated or out-of-order camera samples independently, allow frame-number resets only with newer timestamps, and prevent detection-cache reuse across reconnects. Existing simulation/real frame routing and selected-source traffic state remain distinct.

---

Focused: `python scripts/test_v0524_camera_source_order.py`, `python scripts/test_inference_service.py`, `python scripts/test_remote_camera_multi.py`, `python scripts/test_v0519_emergency_evidence.py`. Windows/ESP live reconnect checks remain pending.

# V0523 — Keyboard-accessible 3D camera

Candidate `0_5_23`, previous `0_5_22`, accepted baseline `0_5_0`. The existing 3D viewport supports keyboard orbit/tilt, zoom and view reset with a visible focus indicator. This is a view-only enhancement: simulator agents, image-coordinate regions, AI detections and ESP camera feeds are untouched.

---

Focused: `python scripts/test_v0523_3d_keyboard.py`, `python scripts/test_v0515_3d_simulation.py`, `npm run typecheck`, `npm run build`. Test keyboard navigation and overlays visually on Windows.

# V0522 — Disconnected/conflicting network safety

Candidate `0_5_22`, previous `0_5_21`, accepted baseline `0_5_0`. Virtual network signals now fail closed on contradictory lamp/phase data and hold a connected movement red when a conflict-linked neighbor's signal state disappears. Existing clearance and priority rules are retained; no physical signal output.

---

Focused: `python scripts/test_v0522_network_disconnect.py` and `python scripts/test_v0514_network_conflicts.py`. Run owner Windows runner and physical camera validation separately.

# V0521 — Same-source ambulance confirmation

Candidate `0_5_21`, previous `0_5_20`, accepted baseline `0_5_0`. Emergency evidence must include two distinct valid, positive camera frames at least 1,000 ms apart from the same source. Positive observations from different camera views alone never confirm a route. Existing protected phases and hardware-disabled behavior are unchanged.

---

Focused: `python scripts/test_v0521_ambulance_single_source.py` plus previous emergency regressions. Windows runner and hardware remain owner checks.

# V0520 — Candidate CI automation

Candidate `0_5_20`, previous `0_5_19`, accepted baseline `0_5_0`. Windows GitHub Actions runs Python compile, project structure, offline regressions and frontend typecheck/build on the feature branch. Local Windows smoke and ESP checks remain pending; no traffic-signal runtime behavior changes.

---

# V0519 — Emergency evidence confirmation candidate

Candidate `0_5_19`, previous `0_5_18`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`. Confirmation is based on distinct source-frame identity, active model and frame timestamps, with at least 1,000 ms between two positive observations. Repeated polls and synchronized camera views cannot satisfy the interval; missing/stale coverage, model change and a newer negative frame clear evidence. Route bounds, expiry, protected transitions, conflict interlock and disabled hardware output remain unchanged.

Focused deterministic checks: `python scripts/test_v0519_emergency_evidence.py` and `python scripts/test_v0512_emergency_corridor.py`. Full Windows owner validation: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. Owner PASS is pending.

---

# V0516 — Crosswalk 3D regression check repair

Candidate `0_5_18`, previous `0_5_17`, accepted baseline `0_5_0`; feature branch `feature/interactive-3d-simulation`. The 3D status panel now reads countdown and object totals from its checked active scene. `0_5_17` fixes moving-agent snapshot assertion order; `0_5_16`'s Crosswalk structure assertion still verifies selected 3D source, aligned edit view, and physical MJPEG fallback.

Static source check: 12/12 focused Crosswalk wiring checks. Full Windows validation still required: use `update_test_run.ps1 -SkipUpdate`, confirm this test and the subsequent suite complete, frontend TypeScript/Vite build and smoke pass, and check all 3D simulation screens with the physical ESP and region editing unaffected. Do not mark PASS until confirmed by the owner.

---

# V0515 — All live simulated camera previews in 3D

Candidate `0_5_15`; previous `0_5_14`; accepted baseline `0_5_0`. Feature branch `feature/interactive-3d-simulation` only.

Run focused `python scripts/test_v0515_3d_simulation.py`, existing simulation-frame, two-pair and Crosswalk regressions, `scripts/check_structure.py`, TypeScript/Vite build and startup/smoke. Use the normal Windows helper with **`-SkipUpdate`** to keep the feature branch checked out.

Manually verify in both simulation camera pairs: Camera Settings and Camera Sources show only 3D for synthetic feeds, Crosswalk Side A/B show two distinct correctly selected 3D sources, Region Editor opens in orbitable 3D, displays region footprints, and switches to Edit regions overhead for draggables that save/reload unchanged coordinates, Camera AI Preview displays 3D boxes/regions with on/off toggles without changing counts, and Dataset Capture shows 3D but stores the original 2D PNG for manual labeling. Check pausing, density changes, source switching, narrow-width layout, simulation Stop, physical ESP previews, live inference, protected signal behavior, legacy 2D training images and Network controllers. Full local Windows/hardware validation and owner PASS pending.

---

# V0514 Release Consistency Repair Candidate

```text
version: 0_5_14
previous_version: 0_5_13
passed_baseline: 0_5_0
status: Network virtual coordination continuation; owner PASS pending
```

- The `0_5_13` preview null-safety code fix remains in place; `0_5_14` fixes the missing patch document and stale current-version documents/constant. No new backend, camera, AI, or signal runtime behavior.
- At PowerShell `D:\AiTL`, run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests`.
- Check the project structure/version gate first, then frontend TypeScript typecheck and Vite build; confirm /health, smoke and normal app startup, Camera AI Preview with missing and available camera status.
- Real ESP tests, full suite where appropriate, and owner acceptance are still required. Accepted baseline stays `0_5_0`.

## Previous candidate 0_5_13

The preceding candidate corrected two nullable camera resolution lookups in `CameraDetectionView`, but omitted the required release bundle, causing the startup structure gate to fail.

---

# V0512 Camera-to-Crosswalk AI Observations Candidate

```text
version: 0_5_12
previous_version: 0_5_11
passed_baseline: 0_5_0
status: Automatic source-to-independent-crosswalk observation bridge candidate
```

## Directional emergency-priority regression

- Run `scripts/test_v0512_emergency_corridor.py` then the full Windows runner.
- A saved Network link defaults Off. Enable A→B, provide two distinct ambulance-class frames over ≥1 s at A, and confirm B's virtual vehicle green extends within its current protected cap. Reverse the route to check direction.
- Reject multiple simultaneous outgoing priority routes from a crosswalk or conflicting incoming destinations.
- Emergency requests must not jump from pedestrian WALK/CLEAR to green; they may expire without service. No real ESP light control or measured jam reduction.

## Focused and full validation

- Run full `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1"`, plus `scripts/test_v0512_camera_crosswalk.py` and `scripts/test_v0512_crosswalk_wiring.py`; check TypeScript build, `/health`, smoke and regression suite.
- Create 2 crosswalks, assign distinct saved simulation/ESP cameras and physical polygon regions on Side A/B, load valid model, enable simulation. Check Network's per-crosswalk `region_class_counts` and `observation_provenance`; switching preview camera must not alter which controllers receive inference.
- Put cars in only Crosswalk A's region; confirm Crosswalk B does not inherit counts. With two views observe average count per class; with only Side A valid observe Side A count with partial status. Valid zero detections must produce zero, not unavailable. Disconnect or stop streaming to confirm stale observations withdrawn.
- On Live Signal Adjustments select `Crosswalk / Region` for a model-supported class, enable and save a class-based scenario, then confirm only that crosswalk can trigger it. Default and previously configured adaptive timing, signals and legacy pipeline must remain functional.
- With camera simulation OFF and live ESP streaming, confirm Network reports a virtual (not physical) signal, the AI region classes update the assigned controller, and stopping the stream marks the virtual controller unavailable.
- Explicitly verify that untyped region data does not claim pedestrians waiting/crossing or vehicle queues and that no physical or adjacent-crosswalk signal commands are issued.
- Backend/frontend test evidence is pending execution on Windows; owner PASS is required.

## Previous V0511 Independent Crosswalk Controllers

# V0511 Independent Crosswalk Simulation Controllers

version: 0_5_11; previous_version: 0_5_10; passed_baseline: 0_5_0.

- Run the full Windows update/test runner, backend /health, TypeScript build and focused `scripts/test_v0511_crosswalk_signals.py` plus `scripts/test_v0511_crosswalk_signal_wiring.py`.
- Create two saved Crosswalks; enable simulation and inspect `GET /api/traffic/crosswalk-signals`. Each must have a separate controller ID/state. Remove one and confirm it disappears; stop simulation and confirm signals unavailable.
- Confirm the Network lamps show each simulated controller's own status, not selected-camera status. Save/reload connection edges; observe connected-crosswalk neighbor metadata but no coordinated phase command.
- Test existing global legacy signal/simulation and camera APIs, default signal timing, live adjustment scenarios and protected phase safety. Independent controllers currently do not automatically ingest per-crosswalk camera observations.
- Accepted baseline 0_5_0; full validation and owner PASS pending.

# V0510 Network signal and live-adjustment candidate (partial)

```text
version: 0_5_10
previous_version: 0_5_9
passed_baseline: 0_5_0
status: Partially implemented signal controls and Network indicators candidate
```

## Validate on Windows

- Run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1"` without `-ChangedTests` from the repo root. Check structural gate, focused `test_v0510_signal_adjustments.py` and `test_v0510_signal_navigation.py`, all regression tests, TypeScript/Vite, health/smoke and startup.
- Under Traffic, open Traffic Light Settings; change the active profile's vehicle green, pedestrian WALK and amber default times within displayed minimum/maximum constraints, Save, reload and verify persistence. Check invalid changes are blocked; original all-red protected phases remain enforced.
- Open Live Signal Adjustments: templates are disabled until enabled. Configure a compatible active legacy zone for ambulance/wheelchair classes and verify active detector support, or use a controlled preview/test scenario. Test crowd thresholds and a crossing still occupied with 3 seconds of clearance remaining, verify protected extension and no conflicting green. Confirm dry-run and stale-data behavior and no emergency flashing-green command.
- Network: select simulator and assign a saved matching simulation camera to Crosswalk A, confirm vehicle and pedestrian bulbs match the active phase and countdown. Other Crosswalk B without independent signal must show unavailable. Trigger a rule at A while A↔B is connected; B displays `not applied here` advisory, **not** a changed signal. Confirm dragging edge labels and crosswalk titles still works, and Save/reload retains links.
- Test with simulation off: indicators display unavailable and do not depict hardware light state. Check existing Signal Control pages, Crosswalk Region Editor, camera preview, network topology and basic signal controller remain unchanged.
- **Explicitly pending:** verified movement conflict topology, independent per-crosswalk controllers and actual adjacent signal coordination; this candidate cannot alter neighbour phase times and cannot command physical traffic signals.
- Full local/Windows validation and owner PASS required. Accepted baseline remains `0_5_0`.

## Previous V059 Global AI and Preview Candidate

```text
version: 0_5_9
previous_version: 0_5_8
passed_baseline: 0_5_0
status: Global AI Models and multi-camera preview candidate
```

## V059 Windows validation

- From repository root run the full `scripts/update_test_run.ps1` (without `-ChangedTests`). Check Python/structure regressions, TypeScript/Vite build, backend startup `/health`, smoke, and app launch.
- Confirm sidebar Traffic precedes AI, AI Models precedes Camera AI Preview, and Settings page is absent. Other navigation/Camera Settings and Traffic behaviors should be unchanged.
- AI Models: upload a small valid `.pt` model with a unique ID; confirm list, load/activate, default, and persist. Refuse duplicate IDs, invalid IDs, empty/oversized files; refuse deletion of the active model. Delete an inactive model and confirm only its run directory is removed. Invalid model weights may upload but must show an activation error.
- Set global confidence and inference interval slider (100–2000 ms), save, refresh app and verify settings remain. Preview should not offer a confidence slider.
- With saved simulated pairs and a valid loaded model, select A, B, C and D independently in Camera AI Preview. Verify frame matches source, class/confidence boxes align, each region uses the correct Side A/B saved polygon, counts appear in the separate region table (not drawn over camera image), and switching preview does not change the selected camera in Camera Settings.
- Connect and stream 2+ ESP cameras; verify inference on both while one is selected, the inactive saved stream still contributes preview detections, disconnected/stale streams show unavailable and do not inherit detections from other cameras. Target frequency depends on CPU/GPU and total camera count. With no model loaded, show no detection boxes; do not fabricate counts.
- Check legacy selected-source `/api/inference/detections`, `/api/traffic/state`, Network, dataset capture, manual camera switching, signal transitions and crosswalk region save/reload. No multi-camera identity fusion or physical signal authorization is introduced.
- Owner PASS pending; accepted baseline stays `0_5_0`.

## Previous V058 AI Group and Network Drag Candidate

```text
version: 0_5_8
previous_version: 0_5_7
passed_baseline: 0_5_0
status: AI workspace and Network drag connections candidate
```

## V058 Windows validation

- Run the full `scripts/update_test_run.ps1` without `-ChangedTests`; check structure and version gate, all Python tests, TypeScript, Vite build, backend health and smoke.
- Confirm Operate lists Camera Settings/Camera Diagnostics before the new AI sidebar group, which contains exactly Camera AI Preview and AI Models. The old AI Detection and Model Registry sidebar entries must not appear elsewhere.
- Camera AI Preview: with a real or connected simulation camera and a loaded model, show the selected camera frame, detection boxes and class filtering. Without a frame, show a clear camera-unavailable message with no fake detections; no model deletion/load controls or automatic model loading on the preview.
- AI Models: list existing trained models, load/set default/unload, change default confidence 0.01–1.00, save it and verify it persists after refresh; backend errors should appear without losing UI state.
- Network: press on Crossing A numbered edge 2, drag until the preview line reaches Crossing B edge 4, release and confirm the link appears at the edge label endpoints. Save network, reload, verify persistence. Drag a crossing title separately; canceled release or same-crossing release must add no connection. Test duplicate rejection and keyboard source/destination activation.
- Existing Crosswalk creation, Region Save, camera assignments, simulation hiding toggle, junction advanced configuration and signal safety must remain unchanged. Owner PASS pending, accepted baseline `0_5_0`.

## Previous V057 Crossing-first Network Candidate

```text
version: 0_5_7
previous_version: 0_5_6
passed_baseline: 0_5_0
status: Crossing-first Network workspace candidate
```

## V057 Windows validation

- Run the full `scripts/update_test_run.ps1` (no `-ChangedTests`) including structural guards, all offline regressions, frontend typecheck/build, backend startup and live smoke.
- Confirm Crosswalks appears above Network and the sidebar no longer labels the page Junction Network.
- In Crosswalks, add and **Save** A and B. Open Network: both boxes must appear automatically. Save another crossing; after the Network page refresh, the new box appears.
- Select A and edge 2, connect to B and edge 4. Drag both boxes, Save network, reload and verify links/positions persist. Remove a link and verify its removal. Delete a crossing in Crosswalks, save and confirm its Network links/position are cleaned.
- Verify active-source-only region observations, correct camera stream/offline state, narrow-viewport map scrolling, and existing advanced junction controls. Connections are metadata, not traffic commands.
- Owner PASS pending; baseline remains `0_5_0`.

## Previous V056 Shared Physical Region Candidate

```text
version: 0_5_6
previous_version: 0_5_5
passed_baseline: 0_5_0
status: Two-view region geometry candidate
```

## V056 validation

- Run the full updater without `-ChangedTests` to check **all** offline regressions, release consistency, frontend TypeScript/build, live smoke and startup.
- Crosswalks → Edit regions: Add Region 1 on Side A and move its vertices to the top; switch to Side B, keep Region 1 selected, move the same region's vertices to the bottom. Return to Side A: its polygon must remain at the top. Change the name and confirm it is the same on both sides.
- Select Save regions, navigate away/reload, confirm the shared name and both independent polygons persist. No backend ID input should appear.
- With a trained model and an assigned active camera, inspect `GET /api/traffic/state` → `crosswalk_region_counts`. The A or B observation should carry the same `physical_region_id` but distinct `camera_region_id`, and only the active source produces counts. Do not add the counts to infer unique objects.
- Confirm old shared and side-scoped regions still load, source switching does not leak counts, and simulator toggles stay hidden by default.
- Owner PASS and hardware validation pending; stable baseline `0_5_0`.

## Previous V055 Regression Alignment Candidate

```text
version: 0_5_5
previous_version: 0_5_4
passed_baseline: 0_5_0
status: Camera/region regression alignment candidate
```

## V055 validation

- Run the full updater (no `-ChangedTests`) once to verify all existing offline tests, in particular `test_camera_settings_page_structure.py` and `test_v0418_camera_region_ui.py`.
- Confirm TypeScript, frontend build, backend `/health`, live smoke and PC Studio startup.
- Manually verify Simulation Camera Pair 1/2 choices behind the brand toggle and independent Crosswalk Side A/B region editing and Save regions.
- No application runtime changes; awaiting owner PASS.

## Previous V054 Camera-Scoped Regions Candidate

```text
version: 0_5_4
previous_version: 0_5_3
passed_baseline: 0_5_0
status: Camera-scoped counting candidate
```

Test Side A/B independent polygons, rename IDs and Save regions; verify GET /api/traffic/state crosswalk_region_counts under trained inference for active camera. Run frontend typecheck/build and smoke. Owner PASS pending.

## V053 Release Consistency Candidate

```text
version: 0_5_3
previous_version: 0_5_2
passed_baseline: 0_5_0
status: V052 release metadata repair candidate
```

## V053 acceptance

- Verify update runner structure/version validation, frontend typecheck/build, backend smoke and Region Editor Save regions persistence.
- V052 Save regions implementation remains unchanged. Owner PASS pending.

## V0501 acceptance

- Run updater with `-ChangedTests`; verify frontend build, smoke and startup.
- On startup simulation options and Experiments are hidden. Click or keyboard-activate AI Traffic Light brand to reveal them; toggle back to hide them. When hiding Experiments, return Dashboard.
- Confirm ESP controls, camera states, saved Side A/B assignments, Regions and existing simulator state are unchanged. Active synthetic inputs remain correctly identified.
- Windows owner PASS pending; stable baseline remains `0_5_0`.

## V050 archive


```text
version: 0_5_0
previous_version: 0_4_24
passed_baseline: 0_5_0
status: Owner-accepted stable release
```

## V050 stable release verification

- The owner explicitly confirmed PASS for V0424 and requested the next stable version. V050 promotes that accepted implementation without new runtime features or code changes.
- Confirm the app reports `0_5_0 Stable` and the Crosswalk layout still shows Side A / Side B camera selectors side by side, with each source state in its own section.
- Verify the previously accepted region translucency, simulation cameras and crosswalk configuration are unchanged. The Windows updater/test runner remains available for optional revalidation; its results have not been observed here.
- Accepted baseline: `0_5_0`.

## Historical V0424 and earlier checks (archival)


```text
version: 0_4_24
previous_version: 0_4_23
passed_baseline: 0_4_14
status: Crosswalk camera-side layout candidate
```

## V0424 Crosswalk camera selector acceptance

- Run `scripts/update_test_run.ps1 -ChangedTests`; verify focused Crosswalk regression, frontend typecheck/build, backend smoke and startup.
- Select a crosswalk. Its Crosswalk layout must show a left Side A and right Side B selector, each directly followed by its current camera status, above the existing schematic.
- No duplicate Side A/B status rows and no bottom Side B selector remain. Narrow widths should stack Side A then Side B without horizontal overflow.
- Select cameras and save/reload; confirm both assignments and statuses persist/update normally, missing-camera warnings work, and the existing simulation preview/region controls are unchanged.
- Candidate V0424 requires Windows visual acceptance; passed baseline remains V0414.

## Historical V0423 and earlier checks (archival)


```text
version: 0_4_23
previous_version: 0_4_22
passed_baseline: 0_4_14
status: Translucent region overlay candidate
```

## V0423 translucent region appearance acceptance

- Run `scripts/update_test_run.ps1 -ChangedTests`, verify the focused region regressions, frontend typecheck/build, backend smoke and startup.
- Open Crosswalks → Edit regions with a simulation camera: unselected regions show a light 10% mint tint and the selected region shows a 22% pale cream tint. Both allow the video beneath to remain visible.
- The selected pale-yellow dashed outline remains 6px and fully opaque; numbered vertices drag, Side A/B toggles work and saving/reloading leaves coordinates unchanged.
- The hidden legacy editor uses the same fill opacity with its existing 7px selected outline. Live AI/simulation region outlines stay unfilled; dataset boxes stay unchanged.
- V0423 awaits owner PASS; accepted baseline remains V0414.

## Historical V0422 and earlier acceptance notes (preserved for reference)

```text
version: 0_4_22
previous_version: 0_4_21
passed_baseline: 0_4_14
status: Responsive text layout and clear selected-region outline candidate
```

## V0422 responsive text and selection acceptance

- Run the standard single-command updater with `-ChangedTests` and confirm regressions, frontend typecheck/build, backend smoke and startup.
- Resize the desktop browser to wide, medium and narrow widths; inspect the sidebar, page/panel headers, buttons, Saved cameras, and status pills. Text should wrap without clipping, with consistent alignment and readable font sizes.
- Inspect Junction Network camera IDs and link names (including long identifiers), Signal Control scenario descriptions, and Simulation Experiment scenarios, tabs and results. Full wording must be readable; on short-height screens, scroll to see all experiment content. Data tables may scroll horizontally.
- In Crosswalks → Edit regions, selected and unselected polygons must have no interior tint; selection should be indicated by a brighter, fully opaque, thicker dashed pale-yellow border with existing draggable vertices.
- Confirm the V0421 second simulation-camera pair remains selectable/usable and saved region geometry is unchanged.
- V0422 remains unaccepted until owner PASS. Accepted baseline stays V0414.

## V0421 two-pair simulation acceptance

- Run the standard one-line update/test runner with `-ChangedTests`; verify both backend camera regressions, frontend TypeScript/build and startup smoke.
- In Camera Settings → New camera → Simulation pair, ensure Pair 1 is saved if absent, then use `Add second simulation pair`. Four saved simulated camera IDs should appear: `simulation_camera`, `simulation_camera_b`, `simulation_camera_c`, `simulation_camera_d`.
- Select each saved camera and check its preview. Pair 1's two views are vertical mirrors; Pair 2 is the same synthetic intersection from a horizontally reflected viewpoint and its mirror. These are two camera pairs on one simulator, not two independent simulations.
- In Crosswalks, assign C/D to the two camera sides of a crosswalk and save/reload. Do not overwrite existing assignments.
- Delete Pair 2 through either C or D and verify Pair 1 survives and continues simulating. Restore Pair 2, delete Pair 1 and verify Pair 2 survives. Physical ESP configurations must stay intact.
- V0422 supersedes V0420's selected translucent overlay; both selected and unselected region interiors remain clear.

## V0420 selected-region visual acceptance

- Run the standard one-line update/test/runner with `-ChangedTests`.
- In Traffic → Crosswalks → Edit regions, selected and unselected polygons have no interior fill. Selection is indicated by a thicker opaque pale-yellow dashed border and draggable numbered vertices.
- Toggle Side A/B and drag vertices to verify selecting/deselecting and geometry persistence. Normal Live AI region overlays should remain fully clear.
- Legacy Region Editor selected polygons use the same light translucent highlight. Dataset object boxes and simulation imagery are unchanged.
- Check TypeScript compilation, production build, live backend smoke, and app startup. V0420 remains a candidate until owner PASS.

## V0419 duplicate CSS rule regression verification

- Run the standard updater with `-ChangedTests` and verify the V0418 regression now inspects both the original cursor declaration and later camera-card background declaration.
- The earlier `assert "cursor: pointer;" in entry` should pass; confirm remaining selected tests, frontend typecheck/build, backend smoke and startup.
- V0418's camera selection, simulation image, region Side A/B buttons, transparency and Simulation active badge alignment are unchanged; continue their visual acceptance.
- Owner-accepted baseline remains V0414; V0419 is a candidate until Windows PASS.

## V0418 camera and region acceptance

- Run the standard one-line updater and confirm the new and historical regressions, frontend TypeScript/build, backend smoke and app startup.
- In Camera Settings → Saved cameras, click a saved ESP or simulation camera card. It should select the camera and update the active preview without duplicating camera-selection services. Verify keyboard focus and busy protection.
- Start PC simulation: the image should show cars and people on the street and crosswalk, **without** text banners, STOP text, traffic signal housings or buses. The simulation signal-state API and safe vehicle/pedestrian timing remain functional.
- In Crosswalks → Edit regions, toggle Side A and Side B with buttons and confirm the correct source preview. Selected regions retain contrasting dashed outlines and numbered drag handles, but normal/selected interiors show the image without translucent fill.
- Check the Simulation active status pill: text should be visually centered. Verify the backup file and regression notes exist at `docs/backups/V0417_PRE_V0418_CODE.md`.
- Accepted baseline remains V0414; V0418 is unaccepted until Windows PASS.

## V0417 transparent region polygon validation

- Run the standard one-line updater and wait for offline regressions, frontend typecheck/build, live smoke and startup.
- In Traffic → Crosswalks → Edit regions, normal and selected region polygons should have no interior fill. Selected polygons should stand out through a thicker warning-colored dashed outline and numbered draggable vertices while remaining completely transparent; unselected regions retain thinner mint outlines.
- In Live AI, regions should overlay live/simulated cameras as unfilled outlines; labels and detections remain legible.
- Legacy Region Editor polygon interior should be transparent for normal and selected states. Dataset Review bounding boxes retain their current display.
- Confirm light and dark modes and saved region geometry are unchanged.

## V0416 Regions wording and navigation validation

- Run the standard one-line updater with `-ChangedTests`; confirm focused Python regressions, TypeScript, build, backend smoke and app startup.
- Traffic sidebar must include Junctions and Crosswalks but no empty Zones page. The Crosswalks → Edit regions workflow must still open its quadrilateral region editor.
- Live AI must show Regions instead of Zones; Signal Control and Traffic Analytics use Region/Regions labels. No visible legacy Zone Editor terminology should remain.
- Verify camera overlays, configured region selection and scenarios still work with saved zone IDs. Internal `zone_id` and `/api/zones` keys deliberately remain unchanged.
- Previous candidate V0415 darker canvas remains included. Owner-accepted stable baseline is V0414.

## V0415 dark canvas validation

- Run the normal single-command updater with `-ChangedTests`.
- Confirm the dark main canvas is `#444557`, slightly darker than accepted V0414 `#4D4E61`; panels, quiet sidebar, mint `#57FFED`, and light mode should remain unchanged.
- Confirm the existing palette and design-structure regressions pass with the new background token; verify TypeScript/frontend build, startup, and live backend smoke.
- Accepted stable baseline is V0414. V0415 remains a candidate until owner PASS.

## V0414 test ownership correction

- Run the normal single-command updater with `-ChangedTests`.
- The previously failing historical `test_v0409_palette_layout.py` should retain palette and junction checks without demanding a removed navigation-heading token.
- `test_v0413_quiet_navigation.py` remains the single focused regression for current sidebar appearance.
- Confirm frontend TypeScript check, production build, backend live smoke and app startup. The workspace CSS and UI are unchanged by V0414.

## V0413 quiet navigation acceptance

- Run the standard one-line update/test/run command; check frontend typecheck/build and live smoke.
- Sidebar group headings (Operate, Traffic, Data & Models) should be small muted uppercase labels with a subtle horizontal divider, not dark boxes with mint borders.
- Selected page should use a solid neutral slate row with bright text and no mint bar or dot; hover should be restrained. Keyboard focus still needs a visible mint outline.
- Test light/dark appearance, navigation across pages, compact window width and preservation of other selection indicators (camera, tabs, toggles).
- The sidebar brand/title remains boxed; Junction Network card, camera and simulation behavior are unchanged.

## V0412 CSS selector regression correction

- Run the standard one-line update/test/run command from the repository root.
- The `test_v0411_junction_card_layout.py` regression should use the last `.junction-node-alerts` rule, not its earlier grouped-selector declaration, and pass.
- Continue to the Windows frontend TypeScript check, production build, startup and live backend smoke.
- Visually confirm the V0411 Junction Network title bar, centered information and four-sided labels. No runtime styling was changed in V0412.

## V0411 Junction Network card acceptance

- Run the standard one-line updater/test/runner.
- On Junction Network, each node should have an independent full-width title bar with junction name and ID; drag anywhere on the title bar.
- Verify traffic vehicle/pedestrian load, camera count, current phase, events and warnings remain centered and fully readable in the main content area.
- Verify numbered edge controls 1–4 sit on the four corresponding sides of the content area, below the title bar, without overlapping information.
- Test very long junction names, IDs, long phase text and narrow windows: fonts adapt to card width, text wraps and node height grows rather than truncating or hiding content.
- Check edge click/selection, crosswalk assignment, drag offset, light/dark themes and frontend TypeScript/build. No hardware required for visual checks.

## V0410 TypeScript repair validation

- Run the standard single-line update/test/run command from the repository root.
- Verify the Camera Settings static regression, TypeScript typecheck (`npm run typecheck`) and frontend production build (`npm run build`) pass.
- Add an ESP32 camera and confirm Save/Connect controls still reflect streaming, busy and missing IP/source ID.
- Verify adding a simulation pair remains available as a separate action. Camera simulation/ESP routing is unchanged.
- Continue V0409 slate/mint and Junction Network visual acceptance, plus live backend smoke.

## V0409 visual acceptance

- Run the standard one-line updater/test/runner from the repository root.
- In Windows dark appearance, confirm a `#4D4E61` canvas, separate dark sidebar, boxed brand/title area, navigation group header strips, raised opaque panels, legible text and `#57FFED` interactive emphasis.
- Confirm light mode still uses the existing light surfaces and deep teal (`#006F66`).
- In Junction Network, inspect junctions at desktop and narrow widths. Edge buttons 1–4 must be inside their respective cards, readable, selectable, and never cover the ID, title, camera count, status, or drag handle.
- Check hover/selection, semantic state pills, forms and vehicle/pedestrian chart series in Camera Settings, Crosswalks, Live AI, Traffic Analytics and Simulation Experiments.
- Validate backend `/health`, the live startup smoke and frontend build. Hardware-only tests remain separate.

## V0408 Windows port-8000 acceptance

- Run the existing one-line update/test/run command. Its preflight regression now executes the real process-identification predicates against Windows process fixtures.
- Port 8000 with system-Python Uvicorn child and verified AiTL virtualenv launcher must restart; unknown or unrelated Python owners must remain protected.
- Confirm backend `/health`, live smoke, frontend startup, and the existing UI behavior. The parent PowerShell host must remain open.
- Hardware tests remain manual. V0408 is a candidate until the owner confirms PASS.

## V0407 backend port-owner validation

- Run the existing one-line update/test/run command. It must keep other processes safe on ports 5173 and 8000.
- If 8000 is held by this project's Uvicorn `--reload` worker, the runner should identify its verified virtualenv parent and restart its process tree without closing unrelated PowerShell windows.
- If 8000 is owned by an unrelated Python program, the runner must refuse to terminate it.
- Verify `/health`, live backend smoke, frontend launch and previously passing Junction Network regression.
- No real hardware required. Owner Windows validation and PASS are pending.

## V0406 test alignment

- Run the existing one-line update/test/run command from the repository root.
- The Junction Network static regression must validate the current simulation/physical camera mode label and the editable primary-camera selector.
- All pending V0405 dark/light theme, frontend typecheck/build and smoke checks remain required.

## V0405 theme and selection acceptance

- From the existing project root run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests`.
- In Windows dark appearance, primary buttons, focus rings, active navigation and selected/toggled controls should use mint `#57FFED` with dark text on filled mint buttons.
- In light appearance, the same interactions should use legible dark teal `#006F66` instead of pale mint on white.
- Inspect Dashboard navigation, Camera Settings selected camera status, Crosswalk list, Junction Network selected edges, Traffic Analytics, Signal Control, Simulation Experiments, Dataset Review and Live AI checked class filters.
- Confirm every selection is also indicated by a dot, underline or border, not color alone; hover and keyboard focus must remain distinct from selection.
- Backend/ESP behavior is unchanged. Frontend build, full startup smoke and owner visual PASS are still required.

## V0404 startup gate repair

- Run the existing one-line update/test/run command from the repository root.
- The structure gate should accept the semantic dark base `#0E1725` instead of demanding `#121212`.
- The V0403 visual regression now checks acceptance of the current palette and rejection of malformed base values.
- Continue the pending V0403 frontend build, backend smoke and light/dark visual acceptance below.

## V0403 visual acceptance

- From the repository root, run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests`.
- Inspect Dashboard, Camera Settings, Crosswalks, Junction Network, Live AI, Dataset Review, Traffic Analytics, Simulation Experiments and Settings in **both Windows light and dark appearance**.
- Confirm legible text, neutral panels, visible input boundaries, clear primary actions and selected navigation, and correct selected tab / segmented view state.
- Test keyboard Tab and simulation panel Left/Right/Home/End navigation. Confirm no clipped layout at typical 1280px and 1920px desktop widths.
- Real/simulation camera and saved data behavior should be unchanged; full frontend build and live smoke must pass before owner PASS.

## V0402 acceptance

- The Crosswalk structure test must recognize the mirrored simulation pair and numbered edges.
- All V0401 functional validation steps below remain required.

## V0401 acceptance

- From repository root run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests`.
- Camera Settings → New Camera → Simulation pair adds exactly two virtual cameras. Select either; Side B must be vertically mirrored.
- Crosswalks → Assign simulation pair sets sides A/B; Save changes and confirm both side previews. Four numbered edge labels appear on the schematic.
- Junction Network edge labels do not obscure card text; dragging from the header does not jump the node centre to the pointer.
- Dashboard, Camera Settings and Crosswalks show no test-ready badges; legacy Camera Sources/Zone Editor disappear from navigation; Zones opens blank.
- Verify real ESP selection and existing crosswalk/junction saved settings are unchanged. Full backend/frontend live smoke and user PASS remain required.


## V0400 startup regression check

- Run `python scripts/test_camera_settings_page_structure.py`: assert simulated previews use the selected simulation branch and physical ESP previews explicitly exclude simulation.
- Run `scripts/update_test_run.ps1 -ChangedTests` from Windows; verify previously blocked startup proceeds through frontend typecheck/build and live smoke.

## Camera and network focused regression

- Create a simulation camera under Camera Settings → New camera and confirm it is selected, previewed and can be removed/re-added without IP or ESP.
- Connect junction 1 edge 2 to junction 2 edge 4; Save network, refresh, and verify the endpoint IDs persist.
- Run `python scripts/test_remote_camera_multi.py`, `python scripts/test_camera_settings_page_structure.py`, `python scripts/test_junction_network_frontend_structure.py`, and `python scripts/test_intersection_network.py`.

## Previous startup regression checks

- Run `python scripts/test_camera_settings_page_structure.py` and `python scripts/test_crosswalks_frontend_structure.py` to confirm both pages remain included in `CAMERA_POLL_PAGES` regardless of neighboring pages.
- Run `scripts/update_test_run.ps1 -ChangedTests` from Windows to verify the full startup pipeline. The original V0324 junction-edge owner checks below remain pending.


## Focused checks

- `python scripts/test_intersection_network.py`: backwards-compatible N/E/S/W defaults, save/reload mappings, duplicate/invalid-reference rejection and untouched signal/controller mapping.
- `python scripts/test_junction_network_frontend_structure.py`: four clickable map labels, edge inspector, typed keys, crosswalk retrieval and missing assignments.
- `python scripts/check_structure.py`, frontend `npm run typecheck`, `npm run build`.

## Owner test

1. Create several named crosswalks in Traffic → Crosswalks.
2. Open Traffic → Junction Network; every card should display N/E/S/W edge buttons, including on unassigned cards.
3. Click each edge and select one crosswalk. Change or clear a mapping. Confirm one crosswalk cannot be assigned to multiple edges.
4. Save network and restart PC Studio; mapping persists while existing cameras, junction dragging, topology links and simulation remain functional.
5. Delete a referenced crosswalk in Crosswalks. Return to Junction Network and click **Refresh crossings**: its ID should be retained and marked Missing, with an option to clear/reassign.
6. Run the full Windows `scripts/update_test_run.ps1` for complete regressions, typecheck/build, backend smoke and UI launch.

No physical hardware is needed for mapping itself. Full owner PASS is pending; baseline stays `0_4_0`.

## V0514 Network coordination verification

- From repository root run the full `scripts/update_test_run.ps1` (or `-ChangedTests` for initial diagnostics); verify static structure, Python regressions, frontend TypeScript/Vite, backend `/health` and smoke.
- Save two Crosswalks, connect them in Network, configure the four conflict checkboxes for the physical movement pairs and enable simulation. With conflicting movements requested, ensure at most one is presented as permitted green. The other node shows a virtual all-red coordinated hold, a paused countdown and the blocking crosswalk.
- After the granted crosswalk completes its vehicle amber/pedestrian-clearance sequence, confirm the blocked movement cannot become permitted until at least two virtual seconds of clearance. Verify it then resumes safely, with no permanent starvation in the tested two-crosswalk case.
- Configure a directed A→B emergency route only after movement conflicts are defined. Confirm two fresh ambulance-class detections over ≥1 s request B's protected vehicle phase, and that A/B never show conflicting virtual greens. Stop the simulator, remove the link or let a request expire and verify no stuck priority.
- Confirm that unconfigured links retain independent behaviour, that saved conflict settings persist, and that legacy simulation, AI camera preview, physical camera connectivity, region counts and Signal Control remain unaffected. No real LED/roadway signals can be commanded.
- This patch includes deterministic `scripts/test_v0514_network_conflicts.py` but Windows/hardware/UI validation and owner PASS remain required.
