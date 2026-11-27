# V0574 — Independent network, region, AI review and reproducible experiment candidate

Candidate `0_5_74`; previous `0_5_73`; accepted baseline `0_5_0`. Updates 31 / U02 and 36 / E02 delivered as software candidate milestones. Updates 30, 33, 37 and 38 partial; Update 28 / S04 remains gated. Owner PASS pending.

Crosswalk editor confirms frame availability, withdraws stale preview, locks mutations during save, preserves failed drafts and maps real pointer input through inverse SVG coordinates with side/pointer ownership. Camera-side assignment and independent region polygons persist. Network protects drafts during failed polls, withdraws stale observations, and qualifies camera reassignment/cancel plus topology link creation/edit/delete/recreation. Dataset Review gates save on matching decoded image and label revision, rejects corrupt/wrong-size images and mismatched save/delete identities, supports actual positive/negative annotation edits, cancellation/deletion, managed build and stale rebuild eligibility. Real-clock CDP trials exercise pointer gestures and capture identity. No backend route, data schema, dependency, signal authority or simulator-default changes.

Application and test qualification: exact [standard CI 46018941752](https://github.com/henrywork059/AiTL/actions/runs/46018941752) on `9e006c900814f65e3e82c76db98fefb815144560` passed compilation, structure, full offline suite, seeded batch, frontend data-access tests, typecheck, build and blocking audit (zero vulnerabilities reported). [Browser CI 46016827486](https://github.com/henrywork059/AiTL/actions/runs/46016827486) on `f18cd41995fd30ef8be305d1d038bca37cc95942` passed all workspace and renderer tests. Later application-qualification commits changed only the two legacy static regression scripts, preserving side-selection and region invariants while checking the new handler. Browser artifact [15205454907](https://github.com/henrywork059/AiTL/actions/runs/46016827486/artifacts/15205454907) SHA-256 `1f672c0f1a6df01ff17b923d3328f60fee6d0960a0ceb9f6b8199071b4f17328` matched; actual region, junction and review screenshots inspected. Tests use synthetic API fixtures, not ESP hardware or trained-model inference. Exact release-bundle standard CI remains pending at publication.

Isolated 120 s queue-model comparisons: 4 seeds (42, 43, 73, 101), 3 demand levels, 12 matched cases, 36 primary policy rows, 96 intersection fairness rows, 4 busy repeats. [Exact standard artifact 15207277149](https://github.com/henrywork059/AiTL/actions/runs/46018941752/artifacts/15207277149) SHA-256 `421b2abbc180b1ded17904f72e61727b00624b1842cb5b36086c4c19292e0c93` independently matched, all 43 member hashes, 216 primary values and 1056 intersection values reconciled; repeated network/local metrics and scenario identity verified. Cooperative minus adaptive pedestrian wait increases in 4/4 light, 3/4 normal and 4/4 busy cases; busy mean +32.125 person-s, vehicle wait mean -305.875 vehicle-s. Secondary pedestrian-aware policy retains adverse cases and vehicle-wait tradeoffs. No tuning, statistical generalization or field claim. Add a standalone read-only evidence verifier (stdlib, no simulator imports) whose exact staged Git blob was matched to locally tested source. It passed two retained full CI archives, and rejected wrong external digest, altered CSV with original or recomputed member hash, and rehashed altered busy repeat. Integrate full batch verification into standard CI and focused smoke/tamper regression; these new CI integrations await exact release CI. Timeline/decision exports are hash-checked, not semantically replayed by this verifier.

Native qualification remains separate: [native CI 46012562415](https://github.com/henrywork059/AiTL/actions/runs/46012562415) and 46011851179 passed; 11 synthetic capture archives/44 images, palette control only, no trusted model holdout. Independently reconciled native/reference normalized timeline metrics and matched resource workloads remain documented in [SIMULATOR_MIGRATION_GATES.md](SIMULATOR_MIGRATION_GATES.md). Finite passage counts match 8 vehicles/14 pedestrians, but native/reference normalized waiting differs (129.4/144.0 vehicle-agent-s; 15.4/57.2 pedestrian-agent-s). Production coordinate calibration/common estimand, trusted detector validation, owner resource budget/Windows and rollback acceptance remain open. Legacy simulator remains default; no public-road signal actuation, no baseline promotion. Partial 30 owner live device/mode acceptance; partial 33 capture/training workflow; partial 37 trusted holdout; partial 38 endurance/master evidence. Updates 32/34 retain dependency gates.

See [PATCH_0_5_74](PATCH_0_5_74.md) and [LOCAL_TESTING](LOCAL_TESTING.md).

---

# V0573 — Independent P4 hardware-first workspace candidate

Candidate `0_5_73`; previous `0_5_72`; accepted baseline `0_5_0`. Update 29 / U01 delivered as candidate; Updates 30–31 / U02 and 33 / U02 partial. Owner PASS pending.

Six navigation groups (Overview, Devices, Network, Simulation, AI Lab, Analytics); all 16 nonlegacy destinations preserved, simulation workspace opt-in. Shared desktop/mobile shell with API/source-mode/version context, skip link and responsive picker. Camera workflow retains transport/profile handlers; device form and diagnostics layout simplified, empty-state media text corrected. Dashboard distinguishes unavailable validation and source status. Crossing inspector selection reveals the selected node, existing keyboard/pointer connections and persisted coordinates retained. Model registry uses strict reads, searchable active/default-prioritized model list, refresh/error handling and responsive upload/settings. Existing backend routes, data formats, model files, camera transport, protected signal decisions and physical restrictions retained. No new dependencies or production backend changes in the independent P4 batch.

Application revision `58b88d4f119347fa8abfaabc592dff10dfaae781`: [standard CI 46008844336](https://github.com/henrywork059/AiTL/actions/runs/46008844336) passed all steps, including 126 discovered offline regression scripts, frontend data-access tests, typecheck, build and blocking npm audit. [Browser CI 46008844185](https://github.com/henrywork059/AiTL/actions/runs/46008844185) passed workspace, renderer and integration trials. Actual headless Windows browser renders of production components with synthetic API fixtures; not field evidence. [Artifact 15203510241](https://github.com/henrywork059/AiTL/actions/runs/46008844185/artifacts/15203510241) SHA-256 `3f88d3f71ef4c2c169eab84d2c2c34226e7e9727440ebe94a742f123b91fac41` independently matched. Corrected camera screenshot inspected: high-contrast empty preview, selected camera B connected but no received frame, stopped stream and camera A unchanged. Corrected network screenshot inspected: one saved link, selected crossing visible, inspector endpoints North [2] / South [4], no verified signal, no assigned cameras. Browser assertions cover camera selection, failed probe/profile retention, retry/start/stop, unverified-frame rejection, other-camera isolation, keyboard link creation/save/visible retention/API reload, model filtering/load/error/recovery, missing validation and responsive navigation/overflow. Exact release commit standard CI pending at publication. Prior native CI 45996915921 passed separately; not an S04 migration acceptance.

Update 29 / U01 delivered as a software candidate (navigation inventory, narrow/desktop browser and existing route/keyboard controls); 28/39 numbered milestones delivered as candidates (71.8%), not owner accepted. Updates 30, 31 and 33 remain partial: owner live Windows camera/editor and simulation-mode checks; comprehensive topology edit/delete, source assignment and stale observation workflow; capture/review/edit/export and training workflow acceptance, respectively. Network fixture proves UI/request/reload behavior; offline backend tests separately prove persistence and invalid-link rejection. Browser model activation uses mock API responses, not actual YOLO inference. Existing scrollable map can clip other nodes while selected node remains visible. Preserve existing light/dark tokens; no further optional restyling. S04/Update 28 remains open: legacy-compatible metrics, production coordinate calibration, trusted detector evidence, owner-PC matched resource/latency budget and acceptance, rollback and migration gates in [SIMULATOR_MIGRATION_GATES.md](SIMULATOR_MIGRATION_GATES.md). Updates 32/34 remain gated. No public-road signal actuation or accepted baseline change.

See [Patch 0_5_73](PATCH_0_5_73.md) and [local testing](LOCAL_TESTING.md).

---

# V0572 — Isolated SUMO two-junction corridor and spillback

Candidate `0_5_72`; previous `0_5_71`; accepted baseline `0_5_0`; Update 27 / S04. Owner PASS pending.

The optional `CorridorSession(seed)` generates a trusted two-junction SUMO fixture with centres 45 m apart and directed vehicle route WA → AB → BE. It reuses the pinned native child process, lane-leader exit-space admission and validated per-junction phase mapping. SUMO owns continuous vehicle motion and persistent IDs. `set_junction_phases` requires explicit virtual phases for both A and B; independently validated permissions, internal vehicle occupancy and pedestrian crossing occupancy restrict each junction. The downstream exit-space gate prevents upstream admission during observed spillback. No new dependency, saved topology integration, HTTP endpoint, frontend selection, physical output or live signal authority; standard shadow and legacy defaults remain unchanged.

Application revision `807864fafaf14eab75721cebddb542943635c774`: [standard CI 45765997190](https://github.com/henrywork059/AiTL/actions/runs/45765997190) and [native SUMO CI 45765997178](https://github.com/henrywork059/AiTL/actions/runs/45765997178) passed. Native JSON inspected in job logs; [artifact 15091264465](https://github.com/henrywork059/AiTL/actions/runs/45765997178/artifacts/15091264465). Seed 42, two 800 s runs, step 0.2 s (4000 steps/run); identical SHA-256 digest d539ea50feb3d0501a7d638d6d04d82e297bc6e4dd0eca6b2ef41b48695a3d63 and all metrics. Per run all 16 distinct vehicle IDs observed entering and leaving AB then arriving; no duplicate snapshot IDs or active/arrived overlap, all 4 pedestrians arrived. Peak observed AB occupancy 4 vehicles; 324 blocked-admission checks with stopped upstream demand and connector front-bumper position below 12 m, of which 207 occurred during downstream all-red. 75 ticks with simultaneous nonempty grants and different requested phases; 4 authorized pedestrian crossing entries and 13 per-person CLEAR occupancy samples. Link travel time is measured from first sampled AB entry to first sampled internal B entry and includes waiting, not door-to-door journey time. Per-ID seconds: v0 109.8, v1 134.0, v2 133.6, v3 111.6, v4 29.0, v5 13.2, v6 13.4, v7 13.2, v8 11.8, v9 13.2, v10 13.4, v11 13.2, v12 12.0, v13 13.2, v14 13.2, v15 13.0. Offline corridor admission, prior native trials, lifecycle and mapping checks, standard compile, structure, offline regressions, frontend tests/typecheck/build and blocking audit passed. Executed synthetic simulation, not field evidence. Exact release commit CI pending at publication.

Restricted eastbound route and explicit phase schedules (B initially all-red for 120 s) deliberately generate congestion; no optimized cooperation, arbitrary configured topology, calibrated demand, general network capacity guarantee, collision certification or superiority claim. The observed peak occupancy is not a universal capacity limit. Sampling at 0.2 s cannot establish continuous-time physical safety. Earlier single-junction controlled fixture still reported emergency-braking warnings. Existing benchmark and normal camera simulation/editor remain unchanged; no new browser or owner Windows/ESP acceptance. Default migration (Update 28) requires separate parity, resource and rollback evidence; do not switch prematurely. No public-road actuation. 27/39 candidates delivered (69.2%); next Update 28 / S04.

See [Patch 0_5_72](PATCH_0_5_72.md).

---

# V0571 — Isolated SUMO lane queues and turning scenarios

Candidate `0_5_71`; previous `0_5_70`; accepted baseline `0_5_0`; Update 26 / S04. Owner PASS pending.

The trusted synthetic SUMO scenario is internally opt-in via `GeneratedSession(seed, lane_scenario=True)`; the standard shadow session and legacy authoritative simulator remain unchanged. The isolated libsumo worker uses the existing validated topology and protected phase upper bound. Seeded finite demand includes straight, left/right turns, a temporary downstream blocker and pedestrians. Lane-leader admission grants at most one vehicle link, rejects insufficient exit space, holds vehicle entry while a pedestrian or vehicle occupies the junction, and allows pedestrian entry only during pedestrian green with no vehicle inside. Yellow, flashing and all-red grant no new entry. No new network listener, frontend mode, API schema, dependency or physical output. Native SUMO retains lane following and motion ownership; the admission function is not an independent physical safety controller.

Application/test revision `b850a2a9077a96cbc4cfcd5931d5244eb84ac57b`: [standard CI 45764874498](https://github.com/henrywork059/AiTL/actions/runs/45764874498) and [native SUMO CI 45764874374](https://github.com/henrywork059/AiTL/actions/runs/45764874374) passed. Actual native JSON printed in job logs; evidence artifact [15091029072](https://github.com/henrywork059/AiTL/actions/runs/45764874374/artifacts/15091029072). Two runs, seed 42, each 440 s at 0.2 s steps (2200 steps); identical SHA-256 digest b5f4f58b81dad25f06447517a09062968c1c3fcebfe82d160d5242b6080946f7 and metrics. Per run: 626 stopped-queue ticks (at least two stopped west-approach vehicles), 577 ticks with a stopped vehicle within 8 m of the lane endpoint, 116 blocked-exit checks during vehicle green, 16 observed authorized vehicle entry transitions, 8 authorized pedestrian crossing-edge entry transitions, 21 pedestrian CLEAR continuation occupancy samples (per-person samples, not necessarily distinct ticks), 116 pedestrian crossing-occupancy ticks, both turn exits CN/CS observed, 17/17 vehicle arrivals including the exit blocker and 4/4 person arrivals. Admission, seeded demand, protected permissions, actual entry transitions and prior shadow lifecycle checks passed; standard compile, structure, offline regressions, frontend data-access tests, typecheck, build and blocking npm audit passed. Evidence is executed synthetic simulation, not field data. Exact release commit CI pending at publication.

Single generated junction, restricted route set and conservative single vehicle-link grant are not a calibrated traffic model, collision certification, live controller comparison or throughput improvement. Capacity check uses observed exit rear-bumper space, not a general network reservation/spillback algorithm; occupancy is sampled at 0.2 s. The earlier controlled fixture reported emergency braking warnings; native fidelity, resource and endurance checks remain outstanding. Normal camera simulation and editor are unchanged; no fresh manual Windows drag/save or physical ESP acceptance. Lane scenario is an internal evaluation seam, not a new UI feature. Default engine migration is reserved for Update 28 after parity/resource gates. No public-road actuation. 26/39 candidates delivered (66.7%); next Update 27 / S04.

See [Patch 0_5_71](PATCH_0_5_71.md).

---

# V0570 — Persistent articulated pedestrians and observed gait

Candidate `0_5_70`; previous `0_5_69`; accepted baseline `0_5_0`; Update 25 / S03. Owner PASS pending.

The optional Three.js preview replaces pedestrian box proxies with persistent volumetric figures (head, torso, separate arms, legs, shoes). PedestrianMotion follows canonical observed positions, bounds interpolation to 450 ms, derives gait from observed displacement, stops gait when stationary/paused, and resets on backwards/large jumps, source/density/clock changes or gaps. RoadRenderer retains mesh groups by existing pedestrian slot ID and color; removes absent groups and disposes owned materials. Shared geometry, mirrored heading, curb elevation and existing animation scheduling are retained. No extrapolation, new crossing authorization, simulator speed or controller change. Legacy CSS remains default and retains the source-coordinate editor and overlays. No API, dependency or physical-output changes.

Application revision `40fcd2ea232ae4a79d16ca17d1b7a16e15cf510c`: [standard CI 45755422048](https://github.com/henrywork059/AiTL/actions/runs/45755422048) and [renderer CI 45755422084](https://github.com/henrywork059/AiTL/actions/runs/45755422084) passed. Standard CI executed three Python lifecycle tests on the actual existing movement helper with fixed phase inputs: both directions, WALK entry, CLEAR continuation, non-WALK curb holds, 30 vs 90 reference pixels/s slow/normal fixtures and seeded reentry. TypeScript motion tests passed for stationary/slow displacement, repeated frames, pause/resume, reentry both directions, reset/source/density/gap and removal; sample independence also asserted. Actual WebGL trial directly asserts persistent pedestrian group reference identity, interpolated position, limb rotation, paused gait freeze and removal; drawing, top view, context loss and cleanup passed. React integration confirms opt-in, source change, editor/overlay fallback, retry and rollback. Both blocking audits reported zero known npm vulnerabilities at execution time. Downloaded [artifact 15087790604](https://github.com/henrywork059/AiTL/actions/runs/45755422084/artifacts/15087790604); SHA-256 31048dfc19e162a4076c5031a3c1f74901f73dd67bba2a91ad2572f953358f35 matches metadata; 1000×650 actual screenshot inspected, three figures (two pavements, one crossing), four vehicles, markings and signals visible, MESH_RENDERER_PASS. Screenshot is a deliberately staged rendering fixture, not proof of safe concurrent movements. Package/lock blobs match b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence: executed synthetic tests, not field data.

Backend pedestrian IDs are recycled slots, not persistent trip identities; reentry snaps rather than traverses the scene. Gait is an illustrative distance-derived animation, not a biomechanical model or accessibility classification. Slow fixture tests do not establish full clearance safety. Non-WALK holds test signal-blocked entry only, not physical obstructions/collision avoidance or downstream capacity. The legacy movement helper is unchanged; renderer may trail observations or snap on reset/pause and is not a safety authority. Small low-poly figures, viewport footprint and Vite large-chunk warning remain. Full Windows owner visual/coordinate drag-save acceptance, native GPU performance, endurance and hardware checks pending. No public-road actuation. Exact release commit CI pending at publication. 25/39 candidates delivered (64.1%); next Update 26 / S04.

See [Patch 0_5_70](PATCH_0_5_70.md) and [local testing](LOCAL_TESTING.md).

---

# V0569 — Persistent vehicle meshes and bounded motion interpolation

Candidate `0_5_69`; previous `0_5_68`; accepted baseline `0_5_0`; Update 24 / S03. Owner PASS pending.

The opt-in Three.js preview uses distinct procedural car, SUV, van and bus meshes with body/cabin proportions, windows, wheels and lights. RoadRenderer retains mesh groups by backend vehicle slot ID and shape signature; removes absent groups and disposes owned materials. VehicleMotion interpolates authoritative observed centers and shortest-angle headings for at most 450 ms, without extrapolation or simulator-clock mutation. Large jumps, backwards straight movement, changed shape, source/density change, clock rollback or a gap over one simulation second reset the affected motion; pause/resume snaps to the authoritative pose. RequestAnimationFrame runs only during active interpolation. The legacy CSS renderer remains default and preserves editing/overlay fallback, camera coordinates and all backend APIs and signal authority. No dependency or physical output changes.

Application revision `8abcac5e874f488604bf084983fbe6976f8159d0`: [standard CI 45753991244](https://github.com/henrywork059/AiTL/actions/runs/45753991244) and [renderer CI 45753991208](https://github.com/henrywork059/AiTL/actions/runs/45753991208) passed. Actual deterministic motion regression covers midpoint/end, interrupted interpolation, duplicate snapshot, synthetic turning and mirrors, east/west reentry, pause/resume, reset, density/source change, removal and frame-sampling independence. Browser trial checks four mesh variants, increasing heights, bus detail and shape signature; actual WebGL drawing, pixel variation, top view, context-loss, repeated disposal, and production React editor/overlay fallback, source switch, retry/rollback and cleanup passed. Persistent group reuse/removal verified by source inspection; the browser test does not directly assert group reference identity across updates. Both blocking npm audits reported zero known vulnerabilities at execution time. Downloaded [artifact 15086527983](https://github.com/henrywork059/AiTL/actions/runs/45753991208/artifacts/15086527983); archive SHA-256 f9211ce575f67c11158eb610d188ee899076c7319293fe0aa3b59a802983e110 matched metadata. Actual 1000×650 screenshot visually inspected: four distinguishable orange vehicles, crossing, markings and signals, MESH_RENDERER_PASS. Package and lock blob hashes match prior validated manifests b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence class: executed synthetic fixtures and browser trials; not field data.

Existing backend IDs are recycled slots, not unique trip IDs; large-jump and direction-based respawn detection is heuristic. Straight-road backend does not execute turning paths; turning tests are synthetic. Interpolation intentionally trails observations, may snap on pause/reset or stale gap, and does not measure controller timing or safety. Direct live mesh-object identity assertion, real Windows owner drag/save round trip, native GPU benchmarks, endurance, full-motion visual acceptance and hardware checks remain outstanding. Models are low-poly; viewport footprint and Vite large-chunk warning remain. Pedestrians remain coarse until Update 25. No public-road actuation. Exact release commit CI pending at publication. 24/39 candidates delivered (61.5%); next Update 25 / S03.

See [Patch 0_5_69](PATCH_0_5_69.md) and [local testing](LOCAL_TESTING.md).

---

# V0568 — Opt-in Three.js road renderer

Candidate `0_5_68`; previous `0_5_67`; accepted baseline `0_5_0`; Update 23 / S03. Owner PASS pending.

Three.js 0.187.0 (MIT, exact pin) renders canonical 1280×720 synthetic road geometry, crossing, markings, pavements/kerbs, virtual signals and coarse agent proxies. SimulationCamera3D retains polling, camera controls and source matching; ThreeRoadView owns WebGL lifecycle and RoadRenderer is shared with the trial. Default CSS rendering is retained; select Three.js preview explicitly for compatible snapshots without visible region/detection overlays. Editor/overlay modes, incompatible or absent snapshots and WebGL failures fall back to legacy. Retry or select Legacy view. No API, coordinate, simulator/controller authority or physical output changes.

Application revision `6380561a6038d0dc3ee85a4bd7cf2bd1a0dc705f`: [standard CI 45740124107](https://github.com/henrywork059/AiTL/actions/runs/45740124107) and [renderer CI 45740124021](https://github.com/henrywork059/AiTL/actions/runs/45740124021) passed. Geometry fixtures cover four mirrored views; isolated WebGL draw/pixel/top-view/context-loss/disposal and React integration tests passed (actual component with mocked read-only synthetic scene: default legacy, opt-in, source A→B, top view, editor/region-overlay fallback, loss/retry, rollback and cleanup). Both audits reported zero known npm vulnerabilities at execution time. Exact generated manifest and lock blobs b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b; eight new lock entries, existing non-root entries unchanged. Earlier 23c screenshot inspected; [23d artifact 15080298917](https://github.com/henrywork059/AiTL/actions/runs/45740124021/artifacts/15080298917) retains screenshot/manifests; no fresh manual inspection claimed. Evidence: executed synthetic browser tests, not field data.

Coarse agents, snapshot stepping, relatively small road footprint, uncalibrated projection and Vite large-chunk warning remain. Detailed vehicle/pedestrian models and interpolation are Updates 24/25. Editor DOM fallback is verified; actual vertex drag/save round trip, full Windows/ESP owner acceptance, native GPU performance, resize stress and matched benchmarks remain pending. No public-road actuation or hardware certification. Exact release commit CI pending at publication. 23/39 candidates delivered (59.0%); next Update 24 / S03.

See [Patch 0_5_68](PATCH_0_5_68.md) and [local testing](LOCAL_TESTING.md).

---

# V0567 — Optional SUMO shadow integration

Candidate `0_5_67`; previous `0_5_66`; accepted baseline `0_5_0`; Update 22 / S02. Owner PASS pending.

The existing CameraFrameService remains authoritative. Optional `MESH_SUMO_SHADOW=1` forwards committed virtual phases to a bounded asynchronous worker and a dedicated libsumo child process through local IPC (no TraCI network listener). Four 50 ms legacy steps produce one 200 ms shadow step; mixed, yellow, flashing or unknown phases grant all-red. Restricted east–west straight vehicle movements and pedestrian crossings are checked against the generated link/conflict matrix, native link mapping and permission readback. Opposing entry is withheld when internal vehicle/crossing edge occupancy is detected. Reset, stop, engine error or backlog overflow invalidate snapshots. Pause stops new legacy ticks, but queued steps may drain. The default is disabled; no automatic dependency install or changes to existing camera/detection/decision/physical outputs. `GET /api/camera/simulation/shadow` is read-only and returns separately labelled synthetic diagnostics; snapshots can lag the authoritative clock.

Evidence class: actually executed synthetic simulation, not field data. Restricted demand, geometry, and illustrative permission cycle differ from the legacy simulator; no matched performance/controller benefit, physical clearance certification, endurance, or owner browser/ESP PASS is established. The native controlled trial and camera integration regression are separate checks, not an end-to-end native PC Studio session. PyPI advisory metadata is time-specific and does not audit bundled native DLLs. Optional packages are pinned to 1.28.0 with wheel hashes; native dependencies are optional and not automatically installed. Keep the existing engine authoritative and opt-in mode restricted to trusted local synthetic evaluation. No public-road actuation, partnership or pilot. Candidate delivery 22/39; next Update 23 / S03 (replacement 3D road renderer).

See [Patch 0_5_67](PATCH_0_5_67.md) and [local testing](LOCAL_TESTING.md). Prior application CI passed; exact release commit CI pending.

---

# V0566 — Frontend dependency security remediation

Candidate `0_5_66`; previous `0_5_65`; accepted baseline `0_5_0`; security prerequisite 21b (not a numbered roadmap completion).

Publish the exact package.json and package-lock.json generated by the read-only Windows dependency trial on parent ccfdc0c86f98e5a76715f16d99f2e083639f802c. Vite 8.2.1 → 8.3.8 (exact direct pin); source-map-js 1.2.1 → 1.2.2 (exact transitive override). Vite's dependency closure also updates Rolldown and its native bindings 1.2.4 → 1.2.19, @oxc-project/types 0.144.0 → 0.156.0, PostCSS 8.5.26 → 8.5.33, nanoid 3.3.18 → 3.3.20, and picomatch 4.0.5 → 4.0.7. Eight optional lock entries added (including WASM/Android bindings, optional @emnapi beta runtime/core, support packages); none removed. Lock entries 68 → 76 including root. Other direct package versions unchanged (React/React DOM 19.2.8, TypeScript 7.0.2, @vitejs/plugin-react 6.0.5). All resolved entries use npm registry HTTPS and SHA-512 integrity. No new app functionality, API, simulator or physical-control changes. Make high-severity npm audit blocking in standard CI; no automatic fixes or force updates.

Audit results are time-specific and do not establish absence of all vulnerabilities. Optional WASM/Android packages (including two pre-release @emnapi packages) are part of the resolver's optional dependency closure, not exercised by the Windows native build. Other platform compatibility, runtime browser/Windows/ESP owner acceptance remain unverified. Remaining direct manifest 'latest' entries retain the existing lock behavior; use npm ci for reproducibility. The security gate for new dependency adoption requires this committed candidate to pass blocking audit, then separate review of the proposed additions. Update 22 remains blocked by pinned SUMO installation, actual smoke scenario and topology validation. No dependency auto-install of SUMO or Three.js, no real-road actuation. Candidate delivery remains 21/39; accepted baseline unchanged.

See [Patch 0_5_66](PATCH_0_5_66.md).

---

# V0565 — Fixed-step legacy simulator adapter

Candidate `0_5_65`; previous `0_5_64`; accepted baseline `0_5_0`; Update 21 / S02.

CameraFrameService delegates timing to a small LegacySimulationAdapter under the existing owner lock. Elapsed monotonic time is represented in integer nanoseconds, accumulated and committed only in 50 ms steps; the old per-refresh fractional step is eliminated. The adapter exposes reset, explicit step, sync, pause, stop and immutable clock snapshot (time, pause, seed). The existing service retains world initialization, seeded RNG, agent movement, render/cache, observation identity and protected signal rules. One existing phase evaluation is shared by both movement types per committed step. Optional constructor-only seed and monotonic clock injection enable reproducible tests without changing HTTP endpoints; production retains the wall-clock-derived default seed. Existing private clock fixture seam is forwarded to the adapter. No new dependencies or physical outputs.

This is a legacy scheduling adapter foundation, not a complete replacement engine. Same seed and elapsed schedule with equivalent phase inputs and no gap over the two-second catch-up bound produce the same committed movement steps; elapsed time above that bound is deliberately discarded, and pause transitions discard uncommitted time since last sync as before (already accumulated substep remainder is retained). Live progression is still demand-driven; it is not an independent background worker, and existing adaptive rule evaluations and evidence expiry still use real time. Scene clock/agents and 2 Hz cached PNG may differ within a render tick; existing API semantics and source IDs are unchanged. Agent lifecycles, renderer, network experiments, and policy are unchanged. The internal clock adapter is only invoked by the camera owner in enabled mode; stop is not an external command interface. No SUMO execution or physical safety claim.

Security gate: previous CI audit JSON (run 45619974507, 25 Nov 2026) identified two high-severity vulnerable packages: locked source-map-js 1.2.1 ([GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), patched range starts at 1.2.2) and direct Vite 8.2.1 ([GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm), audit suggested Vite 8.3.8; additional lower-severity Vite advisories listed in the CI log). The audit step is non-blocking, exited 1, and is not a security PASS. No dependency changes here; package remediation requires regenerated lockfile and fresh audit/build/test evidence. Restrict prototype development server to trusted local access; do not expose it to untrusted networks or open untrusted projects/source maps. Security remediation takes priority before new dependencies; real SUMO smoke and security gates remain blockers for Update 22.

See [Patch 0_5_65](PATCH_0_5_65.md).

---

# V0564 — Simulation engine evaluation foundation

Candidate `0_5_64`; previous `0_5_63`; accepted baseline `0_5_0`; Update 20 / S01.

Update 20 / S01 documents the conditional choice of Eclipse SUMO (external process, eventual single-client TraCI adapter) for microscopic traffic and Three.js (WebGL renderer) for presentation. Added a standalone standard-library Python evaluation harness that generates a synthetic four-arm signalized junction and identical seeded vehicle/pedestrian demand, runs two optional SUMO CLI trials and compares normalized position traces. The current simulator, protected signal controller, camera routes, existing network experiment service and production renderer remain unchanged. No SUMO, TraCI, Three.js or other new dependency installed or adopted.

Engine choice is conditional, not adoption. Before shadow integration, run the optional smoke scenario on a pinned Windows SUMO distribution and validate pedestrian path/crossing geometry, both traces and error handling. Before dependency adoption, inspect existing npm high-severity findings and proposed dependency tree, verify licenses and versions, and document remediation or explicitly accepted residual risk. Compare matched traffic and render workloads; retain rollback, independent safety rules and no physical actuation. No throughput, CPU/RAM, GPU, latency or safety superiority has been demonstrated. Update 21 can proceed with the existing simulator adapter and deterministic clock without new dependencies; Update 22 must wait for engine and security gates.

See [Patch 0_5_64](PATCH_0_5_64.md) and [engine evaluation](SIMULATION_ENGINE_EVALUATION.md).

---

# V0563 — Centralized frontend polling and cancellation

Candidate `0_5_63`; previous `0_5_62`; accepted baseline `0_5_0`; Update 19 / A04.

The existing useSerialPolling hook delegates single-flight task ownership to a small tested pollingScope core. Committed scope changes, disabling and unmount retire an AbortController; the current in-flight promise remains owned until settlement. Retired errors are suppressed, and migrated callers use isCurrent before publishing. apiClient propagates cancellation without logging it as a transport failure or substituting fallback data, preserving genuine API error codes/request IDs and legacy fallback behavior for other callers. Analytics reads use strict typed requests, filter-keyed results and explicit unavailable display; camera AI preview scopes by camera and active model; dataset label reads cancel on capture changes. No new dependencies, endpoints, backend, UI redesign or signal changes.

Cancellation is client-side and does not guarantee the server stops work. Existing zero-argument polling callers retain their legacy publication behavior until individually migrated; scope retirement suppresses hook-level errors but cannot prevent an unguarded callback from writing. AI preview context polling guards publication but its three underlying reads are not aborted. Genuine errors in analytics now show unavailable rather than fallback zero (intentional behavior correction). Full browser rapid-navigation, React lifecycle and owner Windows/ESP checks remain outstanding. No physical output authorized.

Executed the actual pollingScope and apiClient modules with a mocked Node 22 fetch/response test and strict isolated TypeScript compilation, both passed. Git blob hashes for these modules and the test must match the locally tested files. Full checkout unavailable (GitHub DNS failure reproduced); integrated React typecheck/build and full CI pending. Previous 0_5_62 full CI passed ([run 45579569473](https://github.com/henrywork059/AiTL/actions/runs/45579569473)). The new npm test is wired into CI after npm ci. No owner PASS.

Correction 19a (same candidate): [initial CI run 45580743596](https://github.com/henrywork059/AiTL/actions/runs/45580743596) passed compile/structure and reached the historical V059 regression, which incorrectly expected the pre-cancellation `fetchCameraInference(sourceId)` call. Updated the regression to verify signal forwarding, scope retirement, camera/model restart key and the guard before state publication; retained existing settings, model registry and region checks. No runtime source changed. Reproduced the obsolete predicate and checked all 11 current grouped frontend predicates directly against the actual parent source (12 checks including reproduction); these are source checks, not execution of the full Python test. Direct Git checkout remains blocked by DNS resolution. Corrective full CI, frontend runtime test, TypeScript/build and owner PASS pending. Do not advance until corrective CI passes.

Correction 19b (same candidate): [CI run 45591924618](https://github.com/henrywork059/AiTL/actions/runs/45591924618) passed compile, structure, full offline regressions (including corrected V059) and npm ci. The new frontend data-access harness failed before its assertions at `ts.ModuleKind.CommonJS`: the lockfile specifies native TypeScript 7.0.2, which does not provide the old JavaScript compiler API. Replace the harness loader with the locked tsc CLI, an isolated temporary CommonJS project (NodeNext), strict compilation of byte-identical source copies and cleanup in finally. All existing behavioral assertions are retained. Executed corrected harness locally with Node 22.16.0 and available TypeScript 5.8.3; passed strict compilation and mocked runtime checks. Verified all five staged Git blob hashes against tested files (test 6c7e3ca009f0e99be0d116ff9f0aae20c345cc38). Windows CI with locked TypeScript 7.0.2, integrated typecheck/build and owner PASS remain pending; no runtime or dependency changes. GitHub/npm DNS resolution is unavailable in the local environment. npm ci also reported two high-severity vulnerabilities without package/advisory details: investigate via npm audit before any new dependency adoption; do not assume a forced upgrade is safe. Reference: https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ .

See [Patch 0_5_63](PATCH_0_5_63.md).

---

# V0562 — Source-qualified traffic observations

Candidate `0_5_62`; previous `0_5_61`; accepted baseline `0_5_0`; Update 18 / A03.

Selected-source analytics now preserve original source ID, explicit junction mapping, acquisition timestamp/frame and provenance in newly recorded flow events. Flow JSON returns per-source/junction/provenance summaries without cross-camera summation; historical aggregate records remain readable with unknown attribution. The additive traffic_observation projection reports sampled region occupancy, stationary waiting candidates and unavailable state with null metrics. The queue heuristic uses an 8-reference-pixel radius for at least 1000 ms in a configured waiting/queue zone, not calibrated speed or a verified traffic queue. New occupancy history samples retain attribution. Existing aggregate summaries, CSV columns, zones, selected-source architecture and virtual signal authority remain unchanged.

No simultaneous tracking or independent live observations for inactive sources; no unique-object fusion. Stationarity is sampled image-space evidence; unconfirmed objects may still be waiting, and region geometry/calibration are user configured. Lifetime is checked before tracking and before persistence/projection; concurrent source switching and inference remain nontransactional. Existing aggregate history and CSV retain legacy semantics. External uploads are not verified ESP observations. Physical lighting/speaker and actual ESP measurements remain blocked/outstanding.

Locally executed 18 isolated helper cases using stub camera/manager and identity interfaces; compilation passed and Git blob 88909a0b47fc7c427e46609ed430a21278e06c0d matches. Initial isolated test fixture had an incorrect nested retirement token and was corrected before the passing run. Full checkout unavailable due to GitHub DNS failure; new integration regression and full CI pending. Previous CI passed (run 45555018709). Windows/ESP owner PASS pending.

See [Patch 0_5_62](PATCH_0_5_62.md).

---

# V0561 — Scope selected-source tracking by camera and junction

Candidate `0_5_61`; previous `0_5_60`; accepted baseline `0_5_0`; Update 17 / A03.

The existing selected-source tracker now uses an internal scope of camera ID, explicitly matched junction (unmapped remains None), original image dimensions, provenance and acquisition generation/epoch. A scope change, frame-number reset or gap over five seconds starts new tracks; no identity is carried between sources or junctions. A bounded 256-source watermark prevents previously processed cached frames from advancing tracking after switching or active reset. Current same-frame threshold requests may annotate without advancing. Live callers supply immutable ObservationIdentity; expired/mismatched frames receive no tracking annotation, and tracking status endpoints suppress non-current scopes. The existing per-source frame timestamp and five-second freshness policy are reused. No inactive tracker continuation, new inference pipeline, cross-camera fusion, signal policy changes or new public fields. Existing flow events remain legacy aggregate history; independent traffic observation/flow semantics are next in Update 18. Watermarks are process-local and bounded, and an evicted source loses its replay history; no global unique-vehicle claim.

Locally executed the isolated TrackingContinuity helper: 16 targeted assertions plus a bounded-source loop; compilation passed. The helper's staged blob must match the locally tested hash. Full producer/route/tracker regressions were added but not run locally: GitHub DNS resolution failure reproduced. Previous candidate corrective CI passed ([run 45538583036](https://github.com/henrywork059/AiTL/actions/runs/45538583036)); current CI and Windows/ESP owner acceptance pending. Physical throughput/CPU comparison and lighting/speaker gates remain outstanding.

See [Patch 0_5_61](PATCH_0_5_61.md).

---

# V0560 — Separate ATL1 transport framing from camera lifecycle

Candidate `0_5_60`; previous `0_5_59`; accepted baseline `0_5_0`; Update 16 / A04.

Extract the existing ATL1 packet value, exact-length socket wrapper, encoder and decoder into `camera_tcp_transport.py`. The extracted class/function bodies are unchanged. `RemoteCameraService` imports the same symbols at its existing compatibility and monkeypatch seams; it retains socket opening/configuration, worker ownership, stop/join, cancellation, recovery, control requests and frame publication. `RemoteCameraManager` remains the sole registry/session-selection owner. No new transport, duplicate parser, API change, wire change, physical output or freshness policy change.

Three isolated regression groups passed (fragmented framing, socket shutdown, malformed/truncated packets); isolated Python compilation passed. The local test uses the existing 8 MiB frame-size constant in an isolated stub; full checkout could not be cloned because GitHub DNS resolution failed. Full candidate CI, actual ESP throughput/CPU comparison and Windows/ESP owner PASS remain pending. No performance improvement claimed. Previous 0_5_59 CI passed ([run 45518551845](https://github.com/henrywork059/AiTL/actions/runs/45518551845)).

Correction 16a (same candidate): [initial CI run 45531504572](https://github.com/henrywork059/AiTL/actions/runs/45531504572) passed compilation and structure, but stopped at `test_v0310_camera_pipeline.py` because the historical static test still expected `FRAME_MAGIC` in `remote_camera.py`. Updated it to check the extracted codec owner, header format, session import and decoder call; retained the firmware and session assertions. Extended the new transport regression to check compatibility-import object identity. No runtime source or wire protocol change. Reproduced the old predicate failure and checked all 43 corrected static predicates against eight actual files fetched from the parent commit. These checks are a direct source inspection, not execution of the Python scripts. A full local checkout remains unavailable (GitHub DNS resolution failure confirmed); new Python regression execution, full CI and owner/physical validation remain pending.

See [Patch 0_5_60](PATCH_0_5_60.md).

---

# V0559 — Unified camera observation identity

Candidate `0_5_59`; previous `0_5_58`; accepted baseline `0_5_0`; Update 15 / A02.

Internal immutable `ObservationIdentity` projects the existing camera frame's original source ID, PC receive timestamp, frame number, original image dimensions and provenance. Managed ESP frames carry the existing session generation and source retirement epoch; synthetic primary/mirrored frames carry the render's mode generation. Ordinary HTTP uploads are unverified external input. Selected cache promotion retains the same frame and identity. The inference cache uses the shared frame key without changing its semantics. Existing manager lifetime/freshness checks, public JSON, crosswalk detection dictionaries, source coordinates, and selected-source control boundary remain unchanged. Generation metadata records acquisition, not current eligibility; the manager's existing token remains authoritative. Recent valid cached physical frames may still be restored after mode switches with original identity/time, not re-timestamped. No simultaneous multi-junction fusion, physical output or firmware change.

Seven isolated contract assertions and isolated module compilation passed locally. New producer integration regression and existing freshness/safety regressions require full CI; local checkout unavailable (GitHub DNS blocked). Previous candidate CI passed (run 45517777657). Owner Windows/ESP PASS pending; baseline remains `0_5_0`.

See [Patch 0_5_59](PATCH_0_5_59.md).

---

# V0558 — Synthetic speaker preparation

Candidate `0_5_58`; previous `0_5_57`; accepted baseline `0_5_0`; roadmap Update 14 / H07.

The isolated `FakeSpeakerDemo` reuses the existing fake bench controller for a metadata-only demonstration of two predefined notices (`demo_attention`, `demo_accessibility`). Integer normalized volume 1–100% and duration 1–2000 ms are synthetic test bounds, not acoustic levels or certified limits. Explicit test arming is required; invalid or overlapping commands, acknowledgment faults, off, disconnect, generation changes and expiry clear the active notice. No audio playback, arbitrary speech, live route, UI, GPIO, network or firmware integration. Physical speaker integration is BLOCKED: hardware model, amplifier/driver, electrical specifications, acoustic limits, independent hardware fail-safe and controlled-bench authorization remain unconfirmed or unavailable. No acoustic or physical safety validation was performed. Physical lighting also remains blocked. Seven speaker and six lighting regressions passed locally (13 tests); isolated Python compilation passed. Previous candidate CI passed ([run 45515165289](https://github.com/henrywork059/AiTL/actions/runs/45515165289)). Current full CI and owner acceptance pending. See [Patch 0_5_58](PATCH_0_5_58.md).

---

# V0557 — Synthetic lighting preparation

Candidate `0_5_57`; previous `0_5_56`; accepted baseline `0_5_0`; roadmap Update 13 / H07.

The isolated `FakeLightingDemo` delegates binary synthetic pulses to the existing fake bench controller (integer duration 1–2000 ms, acknowledgment bound 100 ms). It is disabled by default, requires explicit test arming, and fails closed on invalid/overlapping requests, acknowledgment faults, disconnect, expiry and generation changes. Status is explicitly simulation-only and physical lighting remains unavailable. No live route, UI, GPIO, network or firmware integration. Physical integration is BLOCKED: lighting model, voltage/current requirements, driver/electrical interface and controlled-bench authorization remain unconfirmed; an independent hardware fail-safe is not implemented. No physical testing or electrical safety validation was performed. Six focused deterministic tests and compilation of the isolated sources passed locally; prior candidate CI passed ([run 45434249530](https://github.com/henrywork059/AiTL/actions/runs/45434249530)). Current full CI and owner acceptance pending. See [Patch 0_5_57](PATCH_0_5_57.md).

---

# V0556 — Fake-only bench output abstraction

Candidate `0_5_56`, previous `0_5_55`, accepted baseline `0_5_0`, roadmap Update 12 / H07.

The isolated bench output module is disabled by default, supports only an in-memory demo indicator and requires explicit test-harness arming. Bounded command leases, matched acknowledgment, timeout checks, disconnect and expiry fail closed. No physical output driver, endpoint, firmware or integration with live traffic control. Local 8/8 deterministic tests passed. Full CI/owner acceptance pending. See [Patch 0_5_56](PATCH_0_5_56.md).

---

# V0555 — Camera setup and connection workflow

Candidate `0_5_55`, previous `0_5_54`, accepted baseline `0_5_0`, roadmap Update 11 / H06.

Validate setup fields before requests, retain saved profiles on failed ESP probes, show source-qualified stale/error/retry status, discard outdated polls and ensure selected-camera status does not combine different devices during refresh. No new endpoints, firmware, registry schema or output commands. See [Patch 0_5_55](PATCH_0_5_55.md). CI and owner Windows/ESP acceptance pending.

---

# V0554 — Derived device capability contract

Candidate `0_5_54`, previous `0_5_53`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`. Roadmap Update 10 / H06.

Add a source-qualified, read-only `device_contract` for each saved ESP and simulation camera, reporting camera input availability, health, and explicitly unavailable lighting/speaker outputs. No new device registry, profile migration, output control or physical actuation. The selected camera's contract is derived from the current source-qualified summary. Existing API and file schemas are preserved.

Pure Python projection: 3/3 local pytest tests passed. CI [run 45425380717](https://github.com/henrywork059/AiTL/actions/runs/45425380717) passed the legacy registry integration, full offline tests, structure, TypeScript and build at commit 1840f9bc. Windows PC Studio/ESP hardware owner acceptance remains pending. See [Patch 0_5_54](PATCH_0_5_54.md).

---

# V0553 — Read-only camera endurance recorder

Candidate `0_5_53`, previous `0_5_52`, accepted baseline `0_5_0`, roadmap Update 09 / H05.

Added a standalone recorder using the existing per-source camera status API. CSV samples and a JSON evidence summary report settings, receiver FPS/age, sequence/reconnect counters and observed outage recovery. CPU/memory require an explicitly identified backend PID and optional psutil; absent data remain null. Exports default outside the Git checkout. No stream control or image decoding.

Local synthetic deterministic regression passed (3/3 tests); complete repository, Windows, frontend and physical ESP acceptance pending. [Patch 0_5_53](PATCH_0_5_53.md).

---

# V0552 — Camera transport diagnostics

Candidate `0_5_52`, previous `0_5_51`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`. Roadmap Update 08 / H05.

Use a monotonic receive clock for frame intervals and smoothed FPS; reset interval and source-sequence baselines on TCP reconnect. Count repeated wire frames without publishing them twice, retain cumulative sequence gaps and count detectable in-session source resets. Expose cached original-frame age, stale/connection state, counters and last error in the existing camera status response and compact detailed panel. All diagnostics are passive: no extra JPEG decoding or public-road output.

The sequence gaps counter counts inferred missing sequence numbers *within* a TCP connection, not IP packet loss or a guaranteed count across disconnects. Reconnect attempts are existing failure/retry attempts, not confirmed successful reconnects. Frame age is based on the original PC receive timestamp (not ESP acquisition latency). Stale means disconnected or older than 5000 ms while streaming; stale FPS is displayed as unavailable. Values reset on explicit stream start; no hardware endurance measurement or latency certification is implied.

Focused zero-argument regression added: `scripts/test_v0552_camera_transport_diagnostics.py`. A full repository checkout, Python regression suite, structure guard, frontend build, CI results and real ESP/Windows test were **not run/verified in this environment**. Owner PASS pending.

See [Patch 0_5_52](PATCH_0_5_52.md).

---

# V0551 — Emergency evidence and virtual network clearance

Candidate `0_5_51`, previous `0_5_50`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Preserve a released movement's two-second virtual clearance record even when the crossing receives a compatible new grant; overlapping release histories conservatively protect both movement types. Sanitize contradictory lamps even without configured links. Emergency confirmation requires two distinct fresh frame IDs from one source at least one second apart, correct model identity and current wall-clock freshness. Withdraw pending priority on lost confirmation, stale evidence, route removal or timeout; retain already committed phase durations and protected local transitions.

See [Patch 0_5_51](PATCH_0_5_51.md). Full Windows owner runner required; no physical output.

---

# V0550 — Stale-input virtual signal fallback

Candidate `0_5_50`, previous `0_5_49`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Adaptive camera observations use original source receive time, bounded by the shorter of the configured timeout and five seconds; missing, future, expired and explicit unavailable inputs are rejected. Replay cannot renew the same timestamp. Persistence is reset after stale/fixed/unavailable evaluations or an elapsed observation gap, even without polling. Unverified named classes are unavailable instead of assumed zero. Fused crosswalk policy observations use the oldest contributing view. Already-committed phase duration and protected transition sequence are preserved; no physical output.

See [Patch 0_5_50](PATCH_0_5_50.md). Full Windows owner runner and simulation acceptance required.

---

# V0549 — Reproducible offline regression execution

Candidate `0_5_49`, previous `0_5_48`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Use one Python offline regression runner in Windows and CI, with deterministic discovery, shared live/hardware exclusions and fail-fast subprocess exit handling. Focused changes to camera/inference/model or camera firmware conservatively run the full suite; missing/deleted tests or empty regression families also fall back to all. Fresh Windows setup targets Python 3.11 and checks native exit codes without replacing an existing venv.

See [Patch 0_5_49](PATCH_0_5_49.md). Full Windows runner still required for owner acceptance; shared offline checks do not start PC Studio.

---

# V0548 — Invalidate disconnected camera observations

Candidate `0_5_48`, previous `0_5_47`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Retire camera delivery before explicit stop, disconnect, reconnect, restart or session replacement. Clear only that source's latest image and increment its observation epoch. Background inference snapshots carry source/mode tokens; invalid or expired predictions are suppressed at completion, API read and virtual-observation forwarding. A mode-generation change invalidates pre-transition predictions, while fresh cached images may still be promoted with their original identity.

See [Patch 0_5_48](PATCH_0_5_48.md). Pull feature branch and run Windows runner with `-SkipUpdate`. Owner PASS pending.

---

# V0547 — Preserve ESP cached-frame identity

Candidate `0_5_47`, previous `0_5_46`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Cache one validated immutable CameraFrame per accepted ESP packet, with its original PC receive timestamp and a globally allocated frame ID. Selection, simulation return and background inference reuse the same object; stale caches remain rejected. Ordinary HTTP uploads still allocate and publish new frames. ESP wire sequence remains a transport diagnostic, not the application frame ID.

See [Patch 0_5_47](PATCH_0_5_47.md). Pull the feature branch and run the Windows runner with `-SkipUpdate`. Verify rapid camera switching, correct source/age, normal streaming and simulation return. Owner PASS pending.

---

# V0546 — ESP worker retirement and recovery

Candidate `0_5_46`, previous `0_5_45`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Guard retired-worker failure, join completion, receive counters/frame metadata and recovery using the worker stop-event identity. Serialize recovery with replacement ESP control commands and recheck ownership around each HTTP stage. Already-issued HTTP calls may finish before replacement control; their stale responses cannot publish state. A frame sink already in progress is not rolled back; cache/source provenance remains Update 03/04.

See [Patch 0_5_46](PATCH_0_5_46.md). Pull the feature branch and run the Windows runner with `-SkipUpdate`. Verify repeated start/stop, ESP reboot/recovery, simulation switching and normal preview. Owner PASS pending.

---

# V0545 — ESP TCP socket-open cancellation

Candidate `0_5_45`, previous `0_5_44`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap Update 01 / H02: After a blocking TCP open returns, recheck cancellation, worker event identity, streaming intent and simulation mode before publishing the socket or connection status. The existing finally block closes the returned socket and clears connection status only when it owns the active socket. This prevents a cancelled opener from replacing a new connection. Ordinary open, read and reconnect behavior, firmware, TCP framing, API shapes and signal behavior remain unchanged.

See [Patch 0_5_45](PATCH_0_5_45.md). Pull the feature branch and run the Windows runner with `-SkipUpdate`. Check repeated ESP start/stop, restart, simulation switching and normal reconnect. Owner PASS pending.

---

# V0544 — ESP TCP post-read cancellation boundary

Candidate `0_5_44`, previous `0_5_43`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Recheck the worker stop event and current simulation mode immediately after a blocking TCP packet read, before counting or publishing the returned packet. A normal complete packet and ordinary EOF retain their existing behavior. This is a narrow receive-loop boundary fix, not a guarantee of atomic cancellation across every worker or mode-transition path.

See [Patch 0_5_44](PATCH_0_5_44.md). Run the feature-branch Windows runner with `-SkipUpdate`; verify ESP stream start/stop, simulation switching, normal preview and recovery. Owner PASS pending.

---

# V0543 — Efficient bounded HTTP camera uploads

Candidate `0_5_43`, previous `0_5_42`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The legacy camera-upload endpoint now buffers accepted image bytes in one bounded bytearray rather than a list of network chunks. The 8 MiB limit, rejection details and strict MIME/image decoding are unchanged; ESP TCP streaming is unaffected.

Pull the feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`; see [Patch 0_5_43](PATCH_0_5_43.md). Confirm valid HTTP uploads and normal ESP/3D simulation behavior. Owner PASS pending.

---

# V0542 — Preserve ESP TCP performance while validating HTTP uploads

Candidate `0_5_42`, previous `0_5_41`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The prior image-decoding candidate affected the shared ESP camera hot path. This correction keeps complete image validation on legacy HTTP uploads while leaving ESP TCP JPEG ingestion at its previously tested low-overhead header check. Camera API errors, 3D simulation and signal safety remain unchanged.

Pull this feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. See [Patch 0_5_42](PATCH_0_5_42.md). Windows/ESP owner PASS pending.

---

# V0541 — Camera frame decoding integrity

Candidate `0_5_41`, previous `0_5_40`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The legacy HTTP camera receiver now rejects truncated or mislabeled PNG/JPEG uploads before they can replace the latest valid frame. An additional pixel-count bound prevents oversized decompression attempts. Existing 3D previews, signal policies and ESP transport are unaffected.

Pull the feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. See [Patch 0_5_41](PATCH_0_5_41.md). Windows/browser owner PASS pending.

---

# V0540 — Bounded HTTP camera uploads

Candidate `0_5_40`, previous `0_5_39`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The camera frame upload endpoint now stops consuming an oversized stream as soon as the existing 8 MiB image limit is exceeded. This prevents avoidable server memory use on oversized requests and retains existing status codes, response envelopes and source validation. This is an incremental camera-ingestion fix, not a change to the ESP camera transport or signal controller.

Run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` after pulling the feature branch. See [Patch 0_5_40](PATCH_0_5_40.md). Windows/browser owner PASS pending.

---

# V0539 — Shared 3D helper regression correction

Candidate `0_5_39`, previous `0_5_38`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Repair the outdated V0523 keyboard-regression assertion following the V0537 extraction of camera coordinate mirroring into `simulation3dMotion.ts`. The keyboard controls, four-view 3D presentation and simulator stay unchanged.

Update this feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. See [Patch 0_5_39](PATCH_0_5_39.md). Owner PASS pending.

---

# V0538 — Restore complete documentation

Candidate `0_5_38`, previous `0_5_37`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

This documentation repair restores the complete release history and local-testing guide. It retains the `0_5_37` fix that mirrors both 3D signal posts with Camera B/C/D and the prior volumetric vehicles, people and smooth reentry work. No runtime behavior changes.

Pull the feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. See [Patch 0_5_38](PATCH_0_5_38.md). Owner PASS remains required before baseline promotion.

---

# V0537 — Correct 3D signal placement across mirrored cameras

Candidate `0_5_37`, previous `0_5_36`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The live 3D signal posts now follow the same horizontal/vertical camera mirror transform as the simulated vehicles and pedestrians. This fixes misplaced posts in Camera B/C/D. The earlier car/SUV/van/bus models and smooth off-screen reentry remain.

Pull the feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. Inspect all four camera views, then confirm PASS before baseline promotion. See [Patch 0_5_37](PATCH_0_5_37.md).

---

# V0536 — Simulation layout regression compatibility

Candidate `0_5_36`, previous `0_5_35`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The V0535 application is unchanged. The legacy layout test now accepts cars, SUVs, vans and buses, while retaining no-banner/no-signal-overlay checks.

Pull the feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. Check the 3D vehicles and pedestrian reentry. See [Patch 0_5_36](PATCH_0_5_36.md). Owner PASS pending.

---

# V0535 — More realistic 3D agents

Candidate `0_5_35`, previous `0_5_34`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

Synthetic traffic now includes car, SUV, van and bus forms. Pedestrians have improved face, hair and clothing details, and no longer slide backwards across the 3D scene when recycled. Protected signals, physical cameras and source-image coordinates are unchanged.

Test the feature branch with `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. Check all four camera viewpoints, pedestrian reentry and different vehicle shapes. See [Patch 0_5_35](PATCH_0_5_35.md). Owner PASS pending.

---

# V0534 — More dimensional 3D simulator

Candidate \`0_5_34\`, previous \`0_5_33\`, accepted baseline \`0_5_0\`, branch \`feature/interactive-3d-simulation\`.

Cars now have cabins, body walls and wheels; pedestrians stand upright with heads and limbs. Vehicles reentering from off-screen no longer appear to race backwards along the roadway. Simulation safety, 2D capture/editor coordinates and physical cameras are unchanged.

Test the feature branch with `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`; check all four camera viewpoints, orbit, zoom, pause and reentry. See [Patch 0_5_34](PATCH_0_5_34.md). Explicit owner PASS pending.

---

# V0533 — Validate explicit simulation tools control

Candidate `0_5_33`, previous `0_5_32`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The V0532 UI remains unchanged; only a regression assertion is corrected to recognize that the dashboard redirect occurs when tools are hidden, not when shown. See [Patch 0_5_33](PATCH_0_5_33.md). Pull the feature branch and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` from the repository root; default runner targets `main`. Windows owner PASS pending.

---

# V0532 — Hallmark sidebar accessibility and clarity

Candidate `0_5_32`, previous `0_5_31`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Simulation tools now use an explicit sidebar button with a pressed state rather than making the whole branding area clickable. Redundant version/tagline and legacy eyebrow copy are removed; version remains in the status bar and navigation behavior is unchanged.

**Test feature branch:** pull `feature/interactive-3d-simulation`, then run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` from the repository root. The default runner targets `main`. Inspect both light and dark appearance, narrow widths and simulation-toggle click/keyboard behavior. See [Patch 0_5_32](PATCH_0_5_32.md). Explicit owner PASS pending.

---

# V0531 — Align legacy simulation structure regression

Candidate `0_5_31`, previous `0_5_30`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

The V0418 camera/region structure regression expected old one-argument vehicle/pedestrian movement calls. After `0_5_30` introduced one shared protected signal phase per simulation step, that old assertion failed CI even though the simulation behavior was intentionally updated. The test now checks the **shared phase lookup and both phase-aware movement calls**. No application runtime or API code changed in this repair; the optimization and physical-output restrictions remain intact.

**Feature-branch owner validation:** pull `feature/interactive-3d-simulation`, then run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` from repository root. Default runner is `main`-only. See [Patch 0_5_31](PATCH_0_5_31.md) and [Local Testing](LOCAL_TESTING.md). Explicit owner PASS pending.

---

# V0530 — Shared protected simulation phase snapshot

Candidate `0_5_30`, previous `0_5_29`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

The 50 ms simulation integrator now evaluates the existing protected signal controller **once** per substep and uses that same phase for both vehicle and pedestrian movement. Previously the same controller was queried separately for each movement type. Existing queue/WALK restrictions, clearance phases, simulated camera frames and 3D viewing behavior are retained. This is a software simulation optimization; physical signal outputs remain disabled.

**Validate the feature branch:** pull `feature/interactive-3d-simulation`, then run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` from the repository root. The default runner targets `main`. See [Patch 0_5_30](PATCH_0_5_30.md) and [Local Testing](LOCAL_TESTING.md). Owner PASS pending.

---

# V0529 — Efficient mirrored simulation camera views

Candidate `0_5_29`, previous `0_5_28`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`. Simulated camera B/C/D now use the current rendered BGR canvas instead of re-decoding the canonical PNG. Image geometry, 3D scene, AI input, and virtual signal protections are unchanged. No physical control is enabled.

**Test this feature branch:** explicitly pull `feature/interactive-3d-simulation` and run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` from the repository root. The default runner pulls `main` and refuses a feature branch. See [Patch 0_5_29](PATCH_0_5_29.md) and [Local Testing](LOCAL_TESTING.md); owner PASS pending.

---

# V0528 — Emergency evidence after camera reconnect

Candidate `0_5_28`, previous `0_5_27`, accepted baseline `0_5_0`. Trust strictly newer source timestamps for emergency-evidence freshness even if a camera reconnect resets its frame counter. A negative reconnect frame clears older ambulance evidence, while equal/older timestamp replays remain rejected. Confirmation still requires two distinct positive observations at least one second apart from the same camera; protected virtual traffic signals and disabled physical outputs are unchanged.

---

# V0527 — Late inference shutdown guard

Candidate `0_5_27`, previous `0_5_26`, accepted baseline `0_5_0`. Discard late inference results when stop is requested, preventing a model call that finishes after the bounded worker shutdown from repopulating cleared per-camera caches or publishing obsolete Crosswalk observations. The prior duplicate-worker guard, normal inference behavior and disabled physical outputs remain unchanged.

---

# V0526 — Inference worker shutdown safety

Candidate `0_5_26`, previous `0_5_25`, accepted baseline `0_5_0`. Preserve a live inference worker reference after its 2-second bounded shutdown join expires; subsequent start attempts cannot create parallel inference threads while the prior worker is running. Clear cached observations as before; no changes to inference results, traffic signals or physical outputs.

---

# V0525 — Per-camera inference diagnostics

Candidate `0_5_25`, previous `0_5_24`, accepted baseline `0_5_0`. Expose measured per-camera inference latency, source frame age and freshness in the existing inference response and Camera AI Preview. Diagnostics are per-source and never fabricated; stale/mismatched-model frames are unavailable for AI overlay. Existing signal decisions and physical-output restrictions are unchanged.

---

# V0524 — Multi-camera source freshness

Candidate `0_5_24`, previous `0_5_23`, accepted baseline `0_5_0`. Harden existing per-source background inference: discard repeated or out-of-order camera samples independently, allow frame-number resets only with newer timestamps, and prevent detection-cache reuse across reconnects. Existing simulation/real frame routing and selected-source traffic state remain distinct.

---

# V0523 — Keyboard-accessible 3D camera

Candidate `0_5_23`, previous `0_5_22`, accepted baseline `0_5_0`. The existing 3D viewport supports keyboard orbit/tilt, zoom and view reset with a visible focus indicator. This is a view-only enhancement: simulator agents, image-coordinate regions, AI detections and ESP camera feeds are untouched.

---

# V0522 — Disconnected/conflicting network safety

Candidate `0_5_22`, previous `0_5_21`, accepted baseline `0_5_0`. Virtual network signals now fail closed on contradictory lamp/phase data and hold a connected movement red when a conflict-linked neighbor's signal state disappears. Existing clearance and priority rules are retained; no physical signal output.

---

# V0521 — Same-source ambulance confirmation

Candidate `0_5_21`, previous `0_5_20`, accepted baseline `0_5_0`. Emergency evidence must include two distinct valid, positive camera frames at least 1,000 ms apart from the same source. Positive observations from different camera views alone never confirm a route. Existing protected phases and hardware-disabled behavior are unchanged.

---

# V0520 — Candidate CI automation

Candidate `0_5_20`, previous `0_5_19`, accepted baseline `0_5_0`. Windows GitHub Actions runs Python compile, project structure, offline regressions and frontend typecheck/build on the feature branch. Local Windows smoke and ESP checks remain pending; no traffic-signal runtime behavior changes.

---

# Start Here — V0519 (ambulance evidence confirmation candidate)

**Candidate:** `0_5_19` | **Previous:** `0_5_18` | **Accepted baseline:** `0_5_0` | **Branch:** `feature/interactive-3d-simulation`.

Emergency priority now requires two distinct, fresh ambulance-positive source frames at least one second apart by frame timestamps. Re-reading one frame, updating another camera, or using synchronized views of one event cannot count as a second observation. Missing/stale coverage, model changes, and a newer negative frame clear confirming evidence. Signal requests remain opt-in, conflict-checked, bounded to 30 seconds and simulation/virtual only; hardware actuation stays disabled.

Run the deterministic emergency regressions, then from the repository root run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` on the feature branch. Windows startup/camera validation and owner PASS remain pending.

---

# Start Here — V0518 (3D status nullability repair)

**Candidate:** `0_5_18` | **Previous:** `0_5_17` | **Accepted baseline:** `0_5_0` | **Branch:** `feature/interactive-3d-simulation`.

The frontend typecheck found three nullable `scene` references in the 3D preview status panel. `0_5_18` uses the already null-checked `activeScene` value for countdown and agent totals. No backend, signal, or camera behavior changes.

From the AiTL repository root, update the feature branch (do not switch to main), then run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -SkipUpdate`. Full Windows startup/visual test and owner PASS pending.

---

# Start Here — V0515 (interactive 3D simulation previews)

**Candidate:** `0_5_15` | **Previous:** `0_5_14` | **Accepted baseline:** `0_5_0`. Work is on `feature/interactive-3d-simulation`, not `main`.

Enable the existing top-left **AI Traffic Light** simulation visibility toggle, then start the PC simulation. All *live simulated camera previews* are now 3D: Camera Settings, Camera Sources, Crosswalks (Side A/B), Crosswalk Region Editor, Camera AI Preview and Dataset Capture. Use drag-to-orbit, wheel/slider zoom, Top and Reset in normal 3D views. Crosswalk Region Editor opens in 3D perspective; select **Edit regions** for the coordinate-aligned 3D overhead view and editable vertices; saved A/B geometries and AI counting stay unchanged. Camera AI Preview overlays existing detection/region coordinates onto its 3D world plane. Real ESP streams are still video, and captured training images stay the original synthetic PNG to avoid corrupting model training and labels.

From your AiTL repository root after switching to the feature branch, use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -SkipUpdate`. Do not run the normal main-pulling updater while on a feature branch. Check the backend regression, TypeScript/Vite build, and simulation visual behavior. Owner PASS pending.

---

# Start Here — V0514

**Current candidate:** `0_5_14` | **Previous candidate:** `0_5_13` | **Accepted baseline:** `0_5_0`.

**Network coordination (same candidate):** In Traffic → Network, edit each saved link's **Conflicting movements** checkboxes. Select only movement combinations that physically intersect (source/destination vehicle or pedestrian). Virtual crosswalk controllers pause blocked phase timers and display coordinated red holds/reasons; once the other crossing clears, a 2 s interlock gap applies. Set the optional emergency route direction if an ambulance should request protected vehicle time at the next crossing. No physical lights can be controlled.

**Fix:** The prior preview nullability repair is retained: camera resolution lookup now allows missing camera status. Candidate `0_5_13` could not start because its release bundle had stale/missing documentation and the frontend version label. `0_5_14` completes that bundle without additional runtime changes.

**Test (PowerShell at `D:\AiTL`):**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Confirm structure/version validation, TypeScript/Vite build, backend /health, launch, and Camera AI Preview (available/unavailable camera). The signal preview remains simulation/virtual only; neither adjacent-crosswalk conflict coordination nor physical traffic-light actuation is enabled. Owner PASS pending.

---

# Start Here — V0512

**Current candidate:** `0_5_12` | **Previous candidate:** `0_5_11` | **Accepted baseline:** `0_5_0`.

**Emergency routing:** Traffic → Network → select a connection → choose **Emergency vehicle route: A→B or B→A**. The default is Off. Two new ambulance-class detection frames spanning at least one second can ask the next crossing's software-only controller for a bounded vehicle-green extension. Pedestrian clearances are not skipped. No physical traffic-light outputs are commanded.

**What changed:** The shared AI inference worker automatically forwards each saved camera's latest detections into its assigned Crosswalk's **independent simulation** controller. Assign cameras and draw Side A/B regions in Crosswalks. Live Signal Adjustments now lists those physical regions for class-based rules (including ambulance/wheelchair only if your loaded model recognizes them). Network shows per-crosswalk counts, camera coverage and signal adjustments.

**Two views:** If a physical region has polygons for both cameras and both frames are fresh and synchronized within 2 seconds, counts are averaged per class. A valid single view uses its count; disconnected/stale frames are unavailable, never interpreted as zero. Region data is snapshot occupancy, not throughput or identity matching.

**Real ESP cameras:** When camera simulation is off, fresh ESP camera AI can update a software-only virtual signal controller. Network labels it virtual (not a physical traffic light). The virtual controller becomes unavailable when detections stop.

**Safety:** Crosswalk regions are not yet typed as waiting/crossing/vehicle queue, so only class-region occupancy triggers can be accurately derived. Slow-walking, waiting and vehicle-queue metrics require explicit region roles/tracking before automatic live activation. Independent controllers remain simulation-only; Network adjacency does not authorize coordinated signals or real hardware actuation.

**Test:** From repository root run:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1"
```

Run full regression, TypeScript/Vite, backend health, simulation, two-camera AI preview and signal tests; owner PASS pending. Existing legacy traffic and global signal APIs unchanged.

---

# Start Here — V0511

Current candidate `0_5_11`; previous `0_5_10`; owner-accepted baseline `0_5_0`.

**Network:** Every saved crosswalk now has its own isolated *simulation-only* signal controller and status, readable at `GET /api/traffic/crosswalk-signals`. Signal indicators on crosswalk boxes read these states separately; configured Network links list neighbors only.

**Limits:** Controllers share default timing and scenario definitions but not runtime phase, observations or test inputs. They do not yet automatically receive all per-crosswalk camera detections and do not coordinate movements. Crosswalk topology defines connection, not whether movements conflict. Existing legacy simulation and traffic APIs remain unchanged; no physical signal control.

**Test:** Run `& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1"` from the repository root, then inspect multiple crosswalks in Network and verify no source-state copying. Full Windows/hardware testing and owner PASS pending.

---

# Start Here — V0510

Current **candidate `0_5_10`**, previous candidate `0_5_9`, owner-accepted baseline `0_5_0`.

**Traffic menu:** New **Traffic Light Settings** and **Live Signal Adjustments** appear after Network. Traffic Light Settings saves protected default phase times using the existing signal profile and signal-rules endpoint. Live Signal Adjustments adds disabled-by-default ranked scenario templates for ambulance-class priority requests, emergency vehicle-green extension, pedestrian/vehicle crowd responses, pedestrian near-end clearance and wheelchair-class accessibility extension. Class-based conditions only work if the active detector, active legacy region and current selected-source traffic observations actually support them; missing observations suppress rules.

**Network:** Each crossing box displays miniature vehicle/pedestrian lights. Only a crossing with a matching source and an active **simulation** signal has a displayed phase/countdown. Other crosses show **No verified crosswalk signal**. A rule winner at one crossing can be shown to a directly connected neighbour as **advisory only / not applied here**. Saved Network connections do NOT establish movement conflicts or safe controller links, so neighbour phase commands are not implemented. There is no emergency flashing green or independent hardware control.

**Validation:** run the full repository runner from your repo root:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1"
```

Verify timing save/reload, rules (including disabled templates), safe signal phase transitions, Network labels and existing camera/network flows. This is a **partial implementation**. Full validation and owner PASS are pending; accepted baseline remains `0_5_0`.

---

# Start Here — V059

Current candidate `0_5_9`, previous candidate `0_5_8`, owner-accepted baseline `0_5_0`.

**Sidebar:** Traffic is now above AI. AI contains AI Models and Camera AI Preview. The Settings page is removed from navigation, while existing settings API and persisted values are preserved.

**AI Models:** Upload an Ultralytics-compatible `.pt` model with a unique ID (limit 200 MiB), load it, set a default or delete an inactive model. Only one loaded model serves all cameras. Detection confidence and the global target inference interval (100–2000 ms slider) are saved here.

**Camera AI Preview:** Choose any registered camera, including saved ESP streams and simulation camera pairs. See its fresh frame, model box/class/confidence overlays and its existing Crosswalk region polygons (Side A/B coordinates). A separate table shows current counts by region and detected class. Camera preview selection does not change the app's active camera selection. Each object is assigned to at most one overlapping region in this preview.

**Limits:** The inference worker runs the single loaded model over fresh camera frames without queuing old frames. Requested intervals are best-effort. Camera AI Preview is separate from existing selected-source traffic analytics/tracking and signal control; there is no cross-camera identity deduplication or public-road traffic authority.

**Run and test:**

```powershell
& ".\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The accepted baseline remains `0_5_0`; V059 is not accepted until owner PASS.

---

# Start Here — V058

Current candidate `0_5_8`, previous candidate `0_5_7`, owner-accepted baseline `0_5_0`.

**Navigation:** Operate now shows Dashboard, Camera Settings and Camera Diagnostics. The new **AI** group contains **Camera AI Preview** and **AI Models**. Camera AI Preview replaces the former AI Detection navigation item, reusing its live inference route. AI Models reuses the former Model Registry route and existing backend model APIs. Model loading/unloading and persistent default confidence are configured there. Camera AI Preview is read-only with respect to model selection, has a session-only confidence slider, and does not display mocked detections as real.

**Network:** Drag from a numbered edge label on one crossing directly onto a numbered edge label on another. The temporary line follows the pointer, and releasing onto a valid destination adds the connection to the draft. Use Save network to persist. Crossing title drag still repositions a box; Save network persists both. Click/keyboard activation of two edge labels also supports connection without a pointer. Existing junction advanced tools, topology schema and signal behavior are unchanged.

## Previous V057

Current candidate `0_5_7`, previous `0_5_6`, accepted baseline `0_5_0`.

**Traffic → Crosswalks** is above **Traffic → Network**. Save a crossing and it automatically appears as a draggable Network box. Select a crossing and its numbered edge 1–4, choose a destination crossing/edge, click Connect crossings, then Save network. Saved camera health is visible for all assigned sources. AI counts are provided only for the currently inferred camera; unobserved crossings are clearly marked. Existing junction topology is preserved under Advanced junction configuration (existing).

## Previous V056

Current candidate `0_5_6` (previous `0_5_5`; accepted baseline `0_5_0`).

**Region Editor:** Add a logical Region 1 once, then switch between Side A and Side B to draw two different polygons for that same physical region. Its name is shared, backend IDs are hidden, and **Save regions** persists both polygons. Older side-scoped regions remain valid and are not silently paired. The backend counts only the active inferred camera; A/B observations are identified separately and cannot be summed without de-duplication.

## Previous V055

Current candidate `0_5_5`, previous candidate `0_5_4`, owner-accepted baseline `0_5_0`.

V055 updates two stale offline regressions (Camera Settings structure and historical V0418 Region Editor side-switch behavior) to reflect existing implemented code. No application runtime code or camera/region data is changed. Use the existing Windows runner to validate all regressions, frontend build and smoke before acceptance.

## Previous V054

Candidate `0_5_4`, previous `0_5_3`, accepted baseline `0_5_0`. The Region Editor creates distinct Side A/B regions and supports an editable backend ID; Save regions persists them. Per-class detection counts are exposed for the active camera only.

## Previous V053

Current candidate `0_5_3`, previous candidate `0_5_2`, accepted baseline `0_5_0`.

V053 repairs V052 release metadata so the update runner can proceed. The Region Editor Save regions button introduced in V052 is unchanged. Toggle the top-left AI Traffic Light panel to show or hide simulation options; default is hidden. The toggle does not stop existing simulation or modify saved assignments.

## Previous V0501 candidate

Current candidate `0_5_1`, accepted baseline `0_5_0`.

## Previous stable release


Current stable release `0_5_0` (previous `0_4_24`); owner-accepted stable baseline `0_5_0`.

The owner confirmed PASS for V0424 and requested the next stable version. V050 is a release-label/documentation promotion of that accepted implementation, with no app, backend, hardware, signal, API or data changes.

V0424 combines each Crosswalk Side A/B camera selector and connection state into one section per side, arranged as two columns above the schematic (stacked on narrow screens). The duplicate status rows and bottom Side B picker are removed. Camera assignment, simulation, regions and V0423 translucent fills are unchanged.

V0423 restores light translucent mint fills (10%) to ordinary Crosswalk regions and pale cream fills (22%) to selected regions, retaining their bright dashed outlines, draggable vertices and visible camera feed; legacy editor matches. Live AI/simulation overlays remain clear. V0422 standardized responsive panel/text alignment and used fully clear selected region interiors with bright outlines. V0421 adds a second selectable saved simulation camera pair (C/D) while retaining Pair 1 (A/B). V0420's pale selected-region fill was superseded by V0422's fully transparent interior and emphasized border. V0419 fixes a duplicate-selector regression test assumption without changing runtime code. V0418 adds clickable Saved cameras, Side A/B toggle buttons, an unannotated cars-and-people simulation, centered status pills, and a pre-patch code archive. V0417 makes region polygon interiors fully transparent while keeping outlines and edit handles. V0416 removes the unused Traffic Zones page and uses Regions terminology throughout the interface while preserving storage/API names. V0415 slightly darkens the dark-mode canvas to #444557 while preserving the accepted sidebar and panel palette. V0414 removes obsolete sidebar assumptions from the historical V0409 regression; V0413 retains the sidebar visual contract. V0413 gives the sidebar quiet slate selection, muted section labels and thin dividers; mint remains reserved for functional emphasis. V0412 corrects a false Junction card layout test assertion by selecting the latest matching CSS rule instead of an earlier grouped rule; V0411's actual UI is unchanged. V0411 restructures Junction Network cards into a separate title bar and centered data with labels 1–4 on the four sides, plus fluid text. V0410 fixes two Camera Settings TypeScript type errors with no behavior or theme change. V0409 applies the slate/mint palette, boxed sidebar headings and inside-card junction edge labels. V0408 verifies the system-Python Uvicorn child directly under AiTL's virtualenv parent (as observed in the Windows process trace). V0407 improved recognition of the Windows Uvicorn reload worker that can own port 8000 during an update. V0406 fixes two stale Junction Network test assertions without changing runtime UI behavior. V0405 adopts the #57FFED dark theme and selected-state indicators. V0404 fixes the outdated structure check blocking the V0403 startup tests; the new palette remains unchanged. V0403 refines shared UI styles without changing the current camera, crossing or junction logic. V0402 fixed a stale Crosswalk regression assertion; functionality from V0401 is unchanged. Camera Settings saves two mirrored simulated cameras. Crosswalks displays numbered edges and can assign the pair to Side A and B. Junction edge labels no longer cover node content, and dragging retains its initial pointer offset. Camera Sources and the old Zone Editor are hidden legacy routes; Traffic → Zones is reserved and intentionally empty.

## Assign crosswalks to junction edges

1. Define your crossings under **Traffic → Crosswalks**.
2. Open **Traffic → Junction Network** and select a junction. Click any **1, 2, 3, 4** label directly on the junction card.
3. Under **Crosswalks by edge** in the inspector, choose a saved crosswalk for the selected side (or **No crosswalk** to clear it). Repeat for the other sides.
4. Click **Save network**. Refreshing or restarting preserves edge assignments. Deleted crosswalks show a missing ID until explicitly corrected.

The numbered labels identify junction connection points regardless of orientation; connections are configuration-only and do not issue signal commands.

## Update and test

```powershell
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Validate UI and full runner before PASS; accepted baseline remains `0_5_0`.
