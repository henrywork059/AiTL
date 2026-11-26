## 0_5_70 — Persistent articulated pedestrians and observed gait (candidate; Update 25 / S03)
- The optional Three.js preview replaces pedestrian box proxies with persistent volumetric figures (head, torso, separate arms, legs, shoes). PedestrianMotion follows canonical observed positions, bounds interpolation to 450 ms, derives gait from observed displacement, stops gait when stationary/paused, and resets on backwards/large jumps, source/density/clock changes or gaps. RoadRenderer retains mesh groups by existing pedestrian slot ID and color; removes absent groups and disposes owned materials. Shared geometry, mirrored heading, curb elevation and existing animation scheduling are retained. No extrapolation, new crossing authorization, simulator speed or controller change. Legacy CSS remains default and retains the source-coordinate editor and overlays. No API, dependency or physical-output changes.
- Application revision `40fcd2ea232ae4a79d16ca17d1b7a16e15cf510c`: [standard CI 45755422048](https://github.com/henrywork059/AiTL/actions/runs/45755422048) and [renderer CI 45755422084](https://github.com/henrywork059/AiTL/actions/runs/45755422084) passed. Standard CI executed three Python lifecycle tests on the actual existing movement helper with fixed phase inputs: both directions, WALK entry, CLEAR continuation, non-WALK curb holds, 30 vs 90 reference pixels/s slow/normal fixtures and seeded reentry. TypeScript motion tests passed for stationary/slow displacement, repeated frames, pause/resume, reentry both directions, reset/source/density/gap and removal; sample independence also asserted. Actual WebGL trial directly asserts persistent pedestrian group reference identity, interpolated position, limb rotation, paused gait freeze and removal; drawing, top view, context loss and cleanup passed. React integration confirms opt-in, source change, editor/overlay fallback, retry and rollback. Both blocking audits reported zero known npm vulnerabilities at execution time. Downloaded [artifact 15087790604](https://github.com/henrywork059/AiTL/actions/runs/45755422084/artifacts/15087790604); SHA-256 31048dfc19e162a4076c5031a3c1f74901f73dd67bba2a91ad2572f953358f35 matches metadata; 1000×650 actual screenshot inspected, three figures (two pavements, one crossing), four vehicles, markings and signals visible, MESH_RENDERER_PASS. Screenshot is a deliberately staged rendering fixture, not proof of safe concurrent movements. Package/lock blobs match b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence: executed synthetic tests, not field data.
- Backend pedestrian IDs are recycled slots, not persistent trip identities; reentry snaps rather than traverses the scene. Gait is an illustrative distance-derived animation, not a biomechanical model or accessibility classification. Slow fixture tests do not establish full clearance safety. Non-WALK holds test signal-blocked entry only, not physical obstructions/collision avoidance or downstream capacity. The legacy movement helper is unchanged; renderer may trail observations or snap on reset/pause and is not a safety authority. Small low-poly figures, viewport footprint and Vite large-chunk warning remain. Full Windows owner visual/coordinate drag-save acceptance, native GPU performance, endurance and hardware checks pending. No public-road actuation. Exact release commit CI pending at publication. 25/39 candidates delivered (64.1%); next Update 26 / S04.

## 0_5_69 — Persistent vehicle meshes and bounded motion interpolation (candidate; Update 24 / S03)
- The opt-in Three.js preview uses distinct procedural car, SUV, van and bus meshes with body/cabin proportions, windows, wheels and lights. RoadRenderer retains mesh groups by backend vehicle slot ID and shape signature; removes absent groups and disposes owned materials. VehicleMotion interpolates authoritative observed centers and shortest-angle headings for at most 450 ms, without extrapolation or simulator-clock mutation. Large jumps, backwards straight movement, changed shape, source/density change, clock rollback or a gap over one simulation second reset the affected motion; pause/resume snaps to the authoritative pose. RequestAnimationFrame runs only during active interpolation. The legacy CSS renderer remains default and preserves editing/overlay fallback, camera coordinates and all backend APIs and signal authority. No dependency or physical output changes.
- Application revision `8abcac5e874f488604bf084983fbe6976f8159d0`: [standard CI 45753991244](https://github.com/henrywork059/AiTL/actions/runs/45753991244) and [renderer CI 45753991208](https://github.com/henrywork059/AiTL/actions/runs/45753991208) passed. Actual deterministic motion regression covers midpoint/end, interrupted interpolation, duplicate snapshot, synthetic turning and mirrors, east/west reentry, pause/resume, reset, density/source change, removal and frame-sampling independence. Browser trial checks four mesh variants, increasing heights, bus detail and shape signature; actual WebGL drawing, pixel variation, top view, context-loss, repeated disposal, and production React editor/overlay fallback, source switch, retry/rollback and cleanup passed. Persistent group reuse/removal verified by source inspection; the browser test does not directly assert group reference identity across updates. Both blocking npm audits reported zero known vulnerabilities at execution time. Downloaded [artifact 15086527983](https://github.com/henrywork059/AiTL/actions/runs/45753991208/artifacts/15086527983); archive SHA-256 f9211ce575f67c11158eb610d188ee899076c7319293fe0aa3b59a802983e110 matched metadata. Actual 1000×650 screenshot visually inspected: four distinguishable orange vehicles, crossing, markings and signals, MESH_RENDERER_PASS. Package and lock blob hashes match prior validated manifests b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b. Evidence class: executed synthetic fixtures and browser trials; not field data.
- Existing backend IDs are recycled slots, not unique trip IDs; large-jump and direction-based respawn detection is heuristic. Straight-road backend does not execute turning paths; turning tests are synthetic. Interpolation intentionally trails observations, may snap on pause/reset or stale gap, and does not measure controller timing or safety. Direct live mesh-object identity assertion, real Windows owner drag/save round trip, native GPU benchmarks, endurance, full-motion visual acceptance and hardware checks remain outstanding. Models are low-poly; viewport footprint and Vite large-chunk warning remain. Pedestrians remain coarse until Update 25. No public-road actuation. Exact release commit CI pending at publication. 24/39 candidates delivered (61.5%); next Update 25 / S03.

## 0_5_68 — Opt-in Three.js road renderer (candidate; Update 23 / S03)
- Three.js 0.187.0 (MIT, exact pin) renders canonical 1280×720 synthetic road geometry, crossing, markings, pavements/kerbs, virtual signals and coarse agent proxies. SimulationCamera3D retains polling, camera controls and source matching; ThreeRoadView owns WebGL lifecycle and RoadRenderer is shared with the trial. Default CSS rendering is retained; select Three.js preview explicitly for compatible snapshots without visible region/detection overlays. Editor/overlay modes, incompatible or absent snapshots and WebGL failures fall back to legacy. Retry or select Legacy view. No API, coordinate, simulator/controller authority or physical output changes.
- Application revision `6380561a6038d0dc3ee85a4bd7cf2bd1a0dc705f`: [standard CI 45740124107](https://github.com/henrywork059/AiTL/actions/runs/45740124107) and [renderer CI 45740124021](https://github.com/henrywork059/AiTL/actions/runs/45740124021) passed. Geometry fixtures cover four mirrored views; isolated WebGL draw/pixel/top-view/context-loss/disposal and React integration tests passed (actual component with mocked read-only synthetic scene: default legacy, opt-in, source A→B, top view, editor/region-overlay fallback, loss/retry, rollback and cleanup). Both audits reported zero known npm vulnerabilities at execution time. Exact generated manifest and lock blobs b72a6215cf357fb94a83f23a8f4af82c6366a75d and faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b; eight new lock entries, existing non-root entries unchanged. Earlier 23c screenshot inspected; [23d artifact 15080298917](https://github.com/henrywork059/AiTL/actions/runs/45740124021/artifacts/15080298917) retains screenshot/manifests; no fresh manual inspection claimed. Evidence: executed synthetic browser tests, not field data.
- Coarse agents, snapshot stepping, relatively small road footprint, uncalibrated projection and Vite large-chunk warning remain. Detailed vehicle/pedestrian models and interpolation are Updates 24/25. Editor DOM fallback is verified; actual vertex drag/save round trip, full Windows/ESP owner acceptance, native GPU performance, resize stress and matched benchmarks remain pending. No public-road actuation or hardware certification. Exact release commit CI pending at publication. 23/39 candidates delivered (59.0%); next Update 24 / S03.

## 0_5_67 — Optional SUMO shadow integration (candidate; Update 22 / S02)
- The existing CameraFrameService remains authoritative. Optional `MESH_SUMO_SHADOW=1` forwards committed virtual phases to a bounded asynchronous worker and a dedicated libsumo child process through local IPC (no TraCI network listener). Four 50 ms legacy steps produce one 200 ms shadow step; mixed, yellow, flashing or unknown phases grant all-red. Restricted east–west straight vehicle movements and pedestrian crossings are checked against the generated link/conflict matrix, native link mapping and permission readback. Opposing entry is withheld when internal vehicle/crossing edge occupancy is detected. Reset, stop, engine error or backlog overflow invalidate snapshots. Pause stops new legacy ticks, but queued steps may drain. The default is disabled; no automatic dependency install or changes to existing camera/detection/decision/physical outputs. `GET /api/camera/simulation/shadow` is read-only and returns separately labelled synthetic diagnostics; snapshots can lag the authoritative clock.
- Executed release-gate evidence for application revision `fc3508e52adf460a19fe32b74c8324903d90e35f`: [standard CI 45737386040](https://github.com/henrywork059/AiTL/actions/runs/45737386040) passed compilation, structure, offline regressions (including camera integration and runtime), frontend regressions/typecheck/build and blocking npm audit (0 reported vulnerabilities). [Native CI 45737386082](https://github.com/henrywork059/AiTL/actions/runs/45737386082), Windows x64 Python 3.10.11, passed exact hash-pinned installation, pip check, version-specific PyPI advisory checks (zero active advisories for all five packages), adapter/child process/runtime tests, native reference and controlled simulation. The earlier [Python 3.11 native CI 45736465611](https://github.com/henrywork059/AiTL/actions/runs/45736465611) also passed the reference trial. Both native-plan reference runs reproduced the TraCI digest `34c24376cf005cdb3d5f9ab0b4aab822847970f49b380fdf139fb0426ee76097` exactly. Each controlled run (seed 42, 300 s, 0.2 s step, 1500 ticks) observed 24 agents, completed 12/12 vehicles and 12/12 pedestrians, and produced digest `28a85055d3ef862650da3fce4aef5e8018f4eb37a9e0f2d3bb017eecf4e7c902`. Observed states were `rrrrrGrrrrrrrGrrrrrr`, `rrrrrrrrrrrrrrrrGGGG`, and `rrrrrrrrrrrrrrrrrrrr`; no simultaneous vehicle/pedestrian grants in the tested fixture. Asynchronous runtime and native failure recovery passed. [Retained artifact 15080205533](https://github.com/henrywork059/AiTL/actions/runs/45737386082/artifacts/15080205533), expires 10 December 2026 09:42 HKT. Results verified from CI logs; newest raw artifact not independently re-inspected in this release step.
- Evidence class: actually executed synthetic simulation, not field data. Restricted demand, geometry, and illustrative permission cycle differ from the legacy simulator; no matched performance/controller benefit, physical clearance certification, endurance, or owner browser/ESP PASS is established. The native controlled trial and camera integration regression are separate checks, not an end-to-end native PC Studio session. PyPI advisory metadata is time-specific and does not audit bundled native DLLs. Optional packages are pinned to 1.28.0 with wheel hashes; native dependencies are optional and not automatically installed. Keep the existing engine authoritative and opt-in mode restricted to trusted local synthetic evaluation. No public-road actuation, partnership or pilot. Candidate delivery 22/39; next Update 23 / S03 (replacement 3D road renderer).

## 0_5_66 — Frontend dependency security remediation (candidate; 21b security prerequisite)
- Publish the exact package.json and package-lock.json generated by the read-only Windows dependency trial on parent ccfdc0c86f98e5a76715f16d99f2e083639f802c. Vite 8.2.1 → 8.3.8 (exact direct pin); source-map-js 1.2.1 → 1.2.2 (exact transitive override). Vite's dependency closure also updates Rolldown and its native bindings 1.2.4 → 1.2.19, @oxc-project/types 0.144.0 → 0.156.0, PostCSS 8.5.26 → 8.5.33, nanoid 3.3.18 → 3.3.20, and picomatch 4.0.5 → 4.0.7. Eight optional lock entries added (including WASM/Android bindings, optional @emnapi beta runtime/core, support packages); none removed. Lock entries 68 → 76 including root. Other direct package versions unchanged (React/React DOM 19.2.8, TypeScript 7.0.2, @vitejs/plugin-react 6.0.5). All resolved entries use npm registry HTTPS and SHA-512 integrity. No new app functionality, API, simulator or physical-control changes. Make high-severity npm audit blocking in standard CI; no automatic fixes or force updates.
- Executed evidence: [dependency trial 45630253510](https://github.com/henrywork059/AiTL/actions/runs/45630253510), job 139261197887, completed successfully on Windows with Node 22. Exact-version resolution, regenerated lock, npm ci, npm ls/version assertions, blocking audit, frontend data-access tests, typecheck and build passed. Audit JSON reported zero known vulnerabilities at run time (0 high, 0 critical, 0 total). Reassembled both complete UTF-8 manifests from ordered base64 log chunks (1 and 39, respectively), parsed JSON and reviewed dependency diff and registry/integrity fields before staging. Previous unchanged application standard CI [45630253344](https://github.com/henrywork059/AiTL/actions/runs/45630253344) passed with non-blocking audit on the old lock. New committed candidate CI and owner PASS remain pending; no local full checkout due to DNS.
- Audit results are time-specific and do not establish absence of all vulnerabilities. Optional WASM/Android packages (including two pre-release @emnapi packages) are part of the resolver's optional dependency closure, not exercised by the Windows native build. Other platform compatibility, runtime browser/Windows/ESP owner acceptance remain unverified. Remaining direct manifest 'latest' entries retain the existing lock behavior; use npm ci for reproducibility. The security gate for new dependency adoption requires this committed candidate to pass blocking audit, then separate review of the proposed additions. Update 22 remains blocked by pinned SUMO installation, actual smoke scenario and topology validation. No dependency auto-install of SUMO or Three.js, no real-road actuation. Candidate delivery remains 21/39; accepted baseline unchanged.

## 0_5_65 — Fixed-step legacy simulator adapter (candidate; Update 21 / S02)
- CameraFrameService delegates timing to a small LegacySimulationAdapter under the existing owner lock. Elapsed monotonic time is represented in integer nanoseconds, accumulated and committed only in 50 ms steps; the old per-refresh fractional step is eliminated. The adapter exposes reset, explicit step, sync, pause, stop and immutable clock snapshot (time, pause, seed). The existing service retains world initialization, seeded RNG, agent movement, render/cache, observation identity and protected signal rules. One existing phase evaluation is shared by both movement types per committed step. Optional constructor-only seed and monotonic clock injection enable reproducible tests without changing HTTP endpoints; production retains the wall-clock-derived default seed. Existing private clock fixture seam is forwarded to the adapter. No new dependencies or physical outputs.
- This is a legacy scheduling adapter foundation, not a complete replacement engine. Same seed and elapsed schedule with equivalent phase inputs and no gap over the two-second catch-up bound produce the same committed movement steps; elapsed time above that bound is deliberately discarded, and pause transitions discard uncommitted time since last sync as before (already accumulated substep remainder is retained). Live progression is still demand-driven; it is not an independent background worker, and existing adaptive rule evaluations and evidence expiry still use real time. Scene clock/agents and 2 Hz cached PNG may differ within a render tick; existing API semantics and source IDs are unchanged. Agent lifecycles, renderer, network experiments, and policy are unchanged. The internal clock adapter is only invoked by the camera owner in enabled mode; stop is not an external command interface. No SUMO execution or physical safety claim.
- Executed three isolated unittest cases against the exact new adapter on Python 3.13.5: different poll partitions (20 identical fixed steps over one second), pause/resume with preserved remainder, capped catch-up, backwards monotonic guard, reset and invalid durations. Both isolated Python files compiled. Verified Git blob hashes: adapter bed0c3ef779d3f4d3a63df10449a0ff940881904; regression 18a9deeff86bc1fb4fd688921cca114e85eca5d6. A fourth regression exercises actual legacy camera agents with injected clock/seed and fixed synthetic phase; it has not been executed locally. Full checkout unavailable due to GitHub DNS failure, so camera integration, old API/signal regressions and current full CI pending. Previous [0_5_64 full CI](https://github.com/henrywork059/AiTL/actions/runs/45619974507) passed. Owner PASS pending.
- Security gate: previous CI audit JSON (run 45619974507, 25 Nov 2026) identified two high-severity vulnerable packages: locked source-map-js 1.2.1 ([GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), patched range starts at 1.2.2) and direct Vite 8.2.1 ([GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm), audit suggested Vite 8.3.8; additional lower-severity Vite advisories listed in the CI log). The audit step is non-blocking, exited 1, and is not a security PASS. No dependency changes here; package remediation requires regenerated lockfile and fresh audit/build/test evidence. Restrict prototype development server to trusted local access; do not expose it to untrusted networks or open untrusted projects/source maps. Security remediation takes priority before new dependencies; real SUMO smoke and security gates remain blockers for Update 22.

## 0_5_64 — Simulation engine evaluation foundation (candidate; Update 20 / S01)
- Update 20 / S01 documents the conditional choice of Eclipse SUMO (external process, eventual single-client TraCI adapter) for microscopic traffic and Three.js (WebGL renderer) for presentation. Added a standalone standard-library Python evaluation harness that generates a synthetic four-arm signalized junction and identical seeded vehicle/pedestrian demand, runs two optional SUMO CLI trials and compares normalized position traces. The current simulator, protected signal controller, camera routes, existing network experiment service and production renderer remain unchanged. No SUMO, TraCI, Three.js or other new dependency installed or adopted.
- Actual local evidence (25 November 2026): Python 3.13.5, Linux x86_64; three offline unittest cases passed and both Python files compiled. The real harness ran and returned exit 2 / blocked with zero trials because sumo and netconvert were absent from PATH; no TraCI, libsumo or CityFlow package installed. GitHub checkout DNS failed; no full local checkout or renderer test. Exact staged Git blobs: harness 448f17187d9c7afcf216438e0915de92f7cb3411, test 81c629182523bd8675d2a5921f0c028d9c754925. Prior full CI passed ([45601046778](https://github.com/henrywork059/AiTL/actions/runs/45601046778)); new CI and owner PASS pending. No measured third-party engine performance or physical validation.
- Engine choice is conditional, not adoption. Before shadow integration, run the optional smoke scenario on a pinned Windows SUMO distribution and validate pedestrian path/crossing geometry, both traces and error handling. Before dependency adoption, inspect existing npm high-severity findings and proposed dependency tree, verify licenses and versions, and document remediation or explicitly accepted residual risk. Compare matched traffic and render workloads; retain rollback, independent safety rules and no physical actuation. No throughput, CPU/RAM, GPU, latency or safety superiority has been demonstrated. Update 21 can proceed with the existing simulator adapter and deterministic clock without new dependencies; Update 22 must wait for engine and security gates.

## 0_5_63 — Centralized frontend polling and cancellation (candidate; Update 19 / A04)
- The existing useSerialPolling hook delegates single-flight task ownership to a small tested pollingScope core. Committed scope changes, disabling and unmount retire an AbortController; the current in-flight promise remains owned until settlement. Retired errors are suppressed, and migrated callers use isCurrent before publishing. apiClient propagates cancellation without logging it as a transport failure or substituting fallback data, preserving genuine API error codes/request IDs and legacy fallback behavior for other callers. Analytics reads use strict typed requests, filter-keyed results and explicit unavailable display; camera AI preview scopes by camera and active model; dataset label reads cancel on capture changes. No new dependencies, endpoints, backend, UI redesign or signal changes.
- Cancellation is client-side and does not guarantee the server stops work. Existing zero-argument polling callers retain their legacy publication behavior until individually migrated; scope retirement suppresses hook-level errors but cannot prevent an unguarded callback from writing. AI preview context polling guards publication but its three underlying reads are not aborted. Genuine errors in analytics now show unavailable rather than fallback zero (intentional behavior correction). Full browser rapid-navigation, React lifecycle and owner Windows/ESP checks remain outstanding. No physical output authorized.
- Executed the actual pollingScope and apiClient modules with a mocked Node 22 fetch/response test and strict isolated TypeScript compilation, both passed. Git blob hashes for these modules and the test must match the locally tested files. Full checkout unavailable (GitHub DNS failure reproduced); integrated React typecheck/build and full CI pending. Previous 0_5_62 full CI passed ([run 45579569473](https://github.com/henrywork059/AiTL/actions/runs/45579569473)). The new npm test is wired into CI after npm ci. No owner PASS.
- Correction 19a (same candidate): [initial CI run 45580743596](https://github.com/henrywork059/AiTL/actions/runs/45580743596) passed compile/structure and reached the historical V059 regression, which incorrectly expected the pre-cancellation `fetchCameraInference(sourceId)` call. Updated the regression to verify signal forwarding, scope retirement, camera/model restart key and the guard before state publication; retained existing settings, model registry and region checks. No runtime source changed. Reproduced the obsolete predicate and checked all 11 current grouped frontend predicates directly against the actual parent source (12 checks including reproduction); these are source checks, not execution of the full Python test. Direct Git checkout remains blocked by DNS resolution. Corrective full CI, frontend runtime test, TypeScript/build and owner PASS pending. Do not advance until corrective CI passes.
- Correction 19b (same candidate): [CI run 45591924618](https://github.com/henrywork059/AiTL/actions/runs/45591924618) passed compile, structure, full offline regressions (including corrected V059) and npm ci. The new frontend data-access harness failed before its assertions at `ts.ModuleKind.CommonJS`: the lockfile specifies native TypeScript 7.0.2, which does not provide the old JavaScript compiler API. Replace the harness loader with the locked tsc CLI, an isolated temporary CommonJS project (NodeNext), strict compilation of byte-identical source copies and cleanup in finally. All existing behavioral assertions are retained. Executed corrected harness locally with Node 22.16.0 and available TypeScript 5.8.3; passed strict compilation and mocked runtime checks. Verified all five staged Git blob hashes against tested files (test 6c7e3ca009f0e99be0d116ff9f0aae20c345cc38). Windows CI with locked TypeScript 7.0.2, integrated typecheck/build and owner PASS remain pending; no runtime or dependency changes. GitHub/npm DNS resolution is unavailable in the local environment. npm ci also reported two high-severity vulnerabilities without package/advisory details: investigate via npm audit before any new dependency adoption; do not assume a forced upgrade is safe. Reference: https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ .

## 0_5_62 — Source-qualified traffic observations (candidate; Update 18 / A03)
- Selected-source analytics now preserve original source ID, explicit junction mapping, acquisition timestamp/frame and provenance in newly recorded flow events. Flow JSON returns per-source/junction/provenance summaries without cross-camera summation; historical aggregate records remain readable with unknown attribution. The additive traffic_observation projection reports sampled region occupancy, stationary waiting candidates and unavailable state with null metrics. The queue heuristic uses an 8-reference-pixel radius for at least 1000 ms in a configured waiting/queue zone, not calibrated speed or a verified traffic queue. New occupancy history samples retain attribution. Existing aggregate summaries, CSV columns, zones, selected-source architecture and virtual signal authority remain unchanged.
- No simultaneous tracking or independent live observations for inactive sources; no unique-object fusion. Stationarity is sampled image-space evidence; unconfirmed objects may still be waiting, and region geometry/calibration are user configured. Lifetime is checked before tracking and before persistence/projection; concurrent source switching and inference remain nontransactional. Existing aggregate history and CSV retain legacy semantics. External uploads are not verified ESP observations. Physical lighting/speaker and actual ESP measurements remain blocked/outstanding.
- Locally executed 18 isolated helper cases using stub camera/manager and identity interfaces; compilation passed and Git blob 88909a0b47fc7c427e46609ed430a21278e06c0d matches. Initial isolated test fixture had an incorrect nested retirement token and was corrected before the passing run. Full checkout unavailable due to GitHub DNS failure; new integration regression and full CI pending. Previous CI passed (run 45555018709). Windows/ESP owner PASS pending.

## 0_5_61 — Scope selected-source tracking by camera and junction (candidate; Update 17 / A03)
- The existing selected-source tracker now uses an internal scope of camera ID, explicitly matched junction (unmapped remains None), original image dimensions, provenance and acquisition generation/epoch. A scope change, frame-number reset or gap over five seconds starts new tracks; no identity is carried between sources or junctions. A bounded 256-source watermark prevents previously processed cached frames from advancing tracking after switching or active reset. Current same-frame threshold requests may annotate without advancing. Live callers supply immutable ObservationIdentity; expired/mismatched frames receive no tracking annotation, and tracking status endpoints suppress non-current scopes. The existing per-source frame timestamp and five-second freshness policy are reused. No inactive tracker continuation, new inference pipeline, cross-camera fusion, signal policy changes or new public fields. Existing flow events remain legacy aggregate history; independent traffic observation/flow semantics are next in Update 18. Watermarks are process-local and bounded, and an evicted source loses its replay history; no global unique-vehicle claim.
- Locally executed the isolated TrackingContinuity helper: 16 targeted assertions plus a bounded-source loop; compilation passed. The helper's staged blob must match the locally tested hash. Full producer/route/tracker regressions were added but not run locally: GitHub DNS resolution failure reproduced. Previous candidate corrective CI passed ([run 45538583036](https://github.com/henrywork059/AiTL/actions/runs/45538583036)); current CI and Windows/ESP owner acceptance pending. Physical throughput/CPU comparison and lighting/speaker gates remain outstanding.

## 0_5_60 — Separate ATL1 transport framing from camera lifecycle (candidate; Update 16 / A04)
- Extract the existing ATL1 packet value, exact-length socket wrapper, encoder and decoder into `camera_tcp_transport.py`. The extracted class/function bodies are unchanged. `RemoteCameraService` imports the same symbols at its existing compatibility and monkeypatch seams; it retains socket opening/configuration, worker ownership, stop/join, cancellation, recovery, control requests and frame publication. `RemoteCameraManager` remains the sole registry/session-selection owner. No new transport, duplicate parser, API change, wire change, physical output or freshness policy change.
- Three isolated regression groups passed (fragmented framing, socket shutdown, malformed/truncated packets); isolated Python compilation passed. The local test uses the existing 8 MiB frame-size constant in an isolated stub; full checkout could not be cloned because GitHub DNS resolution failed. Full candidate CI, actual ESP throughput/CPU comparison and Windows/ESP owner PASS remain pending. No performance improvement claimed. Previous 0_5_59 CI passed ([run 45518551845](https://github.com/henrywork059/AiTL/actions/runs/45518551845)).

- Correction 16a (same candidate): [initial CI run 45531504572](https://github.com/henrywork059/AiTL/actions/runs/45531504572) passed compilation and structure, but stopped at `test_v0310_camera_pipeline.py` because the historical static test still expected `FRAME_MAGIC` in `remote_camera.py`. Updated it to check the extracted codec owner, header format, session import and decoder call; retained the firmware and session assertions. Extended the new transport regression to check compatibility-import object identity. No runtime source or wire protocol change. Reproduced the old predicate failure and checked all 43 corrected static predicates against eight actual files fetched from the parent commit. These checks are a direct source inspection, not execution of the Python scripts. A full local checkout remains unavailable (GitHub DNS resolution failure confirmed); new Python regression execution, full CI and owner/physical validation remain pending.

## 0_5_59 — Unified camera observation identity (candidate; Update 15 / A02)
- Internal immutable `ObservationIdentity` projects the existing camera frame's original source ID, PC receive timestamp, frame number, original image dimensions and provenance. Managed ESP frames carry the existing session generation and source retirement epoch; synthetic primary/mirrored frames carry the render's mode generation. Ordinary HTTP uploads are unverified external input. Selected cache promotion retains the same frame and identity. The inference cache uses the shared frame key without changing its semantics. Existing manager lifetime/freshness checks, public JSON, crosswalk detection dictionaries, source coordinates, and selected-source control boundary remain unchanged. Generation metadata records acquisition, not current eligibility; the manager's existing token remains authoritative. Recent valid cached physical frames may still be restored after mode switches with original identity/time, not re-timestamped. No simultaneous multi-junction fusion, physical output or firmware change.
- Seven isolated contract assertions and isolated module compilation passed locally. New producer integration regression and existing freshness/safety regressions require full CI; local checkout unavailable (GitHub DNS blocked). Previous candidate CI passed (run 45517777657). Owner Windows/ESP PASS pending; baseline remains `0_5_0`.

## 0_5_58 — Synthetic speaker preparation (candidate; roadmap Update 14 / H07; physical integration BLOCKED)
- The isolated `FakeSpeakerDemo` reuses the existing fake bench controller for a metadata-only demonstration of two predefined notices (`demo_attention`, `demo_accessibility`). Integer normalized volume 1–100% and duration 1–2000 ms are synthetic test bounds, not acoustic levels or certified limits. Explicit test arming is required; invalid or overlapping commands, acknowledgment faults, off, disconnect, generation changes and expiry clear the active notice. No audio playback, arbitrary speech, live route, UI, GPIO, network or firmware integration.
- Physical speaker integration is BLOCKED: hardware model, amplifier/driver, electrical specifications, acoustic limits, independent hardware fail-safe and controlled-bench authorization remain unconfirmed or unavailable. No acoustic or physical safety validation was performed. Physical lighting also remains blocked. Seven speaker and six lighting regressions passed locally (13 tests); isolated Python compilation passed. Previous candidate CI passed ([run 45515165289](https://github.com/henrywork059/AiTL/actions/runs/45515165289)). Current full CI and owner acceptance pending.

## 0_5_57 — Synthetic lighting preparation (candidate; roadmap Update 13 / H07; physical integration BLOCKED)
- The isolated `FakeLightingDemo` delegates binary synthetic pulses to the existing fake bench controller (integer duration 1–2000 ms, acknowledgment bound 100 ms). It is disabled by default, requires explicit test arming, and fails closed on invalid/overlapping requests, acknowledgment faults, disconnect, expiry and generation changes. Status is explicitly simulation-only and physical lighting remains unavailable. No live route, UI, GPIO, network or firmware integration.
- Physical integration is BLOCKED: lighting model, voltage/current requirements, driver/electrical interface and controlled-bench authorization remain unconfirmed; an independent hardware fail-safe is not implemented. No physical testing or electrical safety validation was performed. Six focused deterministic tests and compilation of the isolated sources passed locally; prior candidate CI passed ([run 45434249530](https://github.com/henrywork059/AiTL/actions/runs/45434249530)). Current full CI and owner acceptance pending. Accepted baseline `0_5_0`.

## 0_5_56 — Fake-only bench output abstraction (candidate; roadmap Update 12 / H07)
- Added disabled-by-default fake adapter/controller with explicit test arming, bounded leases, matched acknowledgment, timeout checks, disconnect, off and watchdog expiry. No physical output or live application integration.
- Eight deterministic local tests and compilation passed. Previous candidate 0_5_55 CI passed; current CI and owner acceptance pending. Accepted baseline `0_5_0`.

## 0_5_55 — Device setup and connection workflow (candidate; roadmap Update 11 / H06)
- Prevent cross-camera status mixing when selection changes during a refresh. Preserve per-source failed initial probe diagnostics without claiming a configured connection. Validate saved camera IP, identity and settings before requests; show explicit retry, waiting/stale/error states, and guard current-source controls and preview from stale polls.
- Added fake-HTTP setup/retry/persistence/selection regression and extended UI wiring regression. Full CI and Windows/ESP owner PASS pending. Previous `0_5_54`, accepted baseline `0_5_0`.

## 0_5_54 — Read-only device capability/health contract (candidate; roadmap Update 10 / H06)
- Project each saved ESP/simulation camera into a versioned `device_contract` using the existing remote-camera manager: source-owned input availability, explicit health state, and unavailable lighting/speaker outputs. Add matching frontend types and an additive selected-camera projection; no second registry, persisted schema migration, output command or image decode.
- Pure projection regression passed locally (3/3 pytest tests); legacy profile/round-trip integration regression added. CI run 45424883577 exposed a stale V0525 diagnostics fixture without the V0548 source token; correct that fixture on the same candidate and require a new CI result. Runtime freshness interlock is unchanged. Corrective CI [run 45425380717](https://github.com/henrywork059/AiTL/actions/runs/45425380717) passed full offline regressions, structure, frontend typecheck/build on commit 1840f9bc; owner Windows/ESP PASS pending. Previous `0_5_53`, accepted baseline `0_5_0`.

## 0_5_53 — Read-only camera endurance recorder (candidate; roadmap Update 09 / H05)
- Added a standalone status-sampling recorder with streaming per-camera CSV samples and bounded-memory JSON aggregates for frame age, receiver FPS/interval, inferred wire sequence gaps, duplicated packets, reconnect/session counters, observed outages, saved settings and change markers. Optional backend PID/psutil captures CPU and memory; no stream-control change, image decoding, or hardware output. Outputs default outside checkout.
- Synthetic zero-argument regression passed locally (3/3 via pytest and direct main); complete suite, structural checker, CI and owner Windows/ESP acceptance unverified. Previous `0_5_52`, accepted baseline `0_5_0`.

## 0_5_52 — Camera transport diagnostics (candidate; roadmap Update 08 / H05)
- Use monotonic receive timing for FPS and interval statistics, reset measurement/sequence baselines on TCP socket reopening, suppress repeated source packets and count detectable in-stream sequence resets. Preserve original cached-frame age and expose passive per-camera diagnostics, connection state, errors and counters in the existing status/UI contract; no JPEG re-decode.
- Add focused deterministic regression for packets, monotonic clocks, stale state, retired workers and independent sessions. Full local suite, CI and owner Windows/ESP PASS remain unverified. Previous `0_5_51`, accepted baseline `0_5_0`.

## 0_5_51 — Emergency evidence and virtual network clearance (candidate; roadmap Update 07 / A01)
- Preserve a released movement's two-second virtual clearance record even when the crossing receives a compatible new grant; overlapping release histories conservatively protect both movement types. Sanitize contradictory lamps even without configured links. Emergency confirmation requires two distinct fresh frame IDs from one source at least one second apart, correct model identity and current wall-clock freshness. Withdraw pending priority on lost confirmation, stale evidence, route removal or timeout; retain already committed phase durations and protected local transitions.
- Local pure coordinator and evidence checks passed; full integration/CI/owner PASS pending. Previous `0_5_50`, accepted baseline `0_5_0`.

## 0_5_50 — Stale-input virtual signal fallback (candidate; roadmap Update 06 / A01)
- Adaptive camera observations use original source receive time, bounded by the shorter of the configured timeout and five seconds; missing, future, expired and explicit unavailable inputs are rejected. Replay cannot renew the same timestamp. Persistence is reset after stale/fixed/unavailable evaluations or an elapsed observation gap, even without polling. Unverified named classes are unavailable instead of assumed zero. Fused crosswalk policy observations use the oldest contributing view. Already-committed phase duration and protected transition sequence are preserved; no physical output.
- Five reproduced defects; ten isolated checks passed. Previous `0_5_49`, accepted baseline `0_5_0`; full CI/owner PASS pending.

## 0_5_49 — Reproducible offline regression execution (candidate; roadmap Update 05 / H04)
- Use one Python offline regression runner in Windows and CI, with deterministic discovery, shared live/hardware exclusions and fail-fast subprocess exit handling. Focused changes to camera/inference/model or camera firmware conservatively run the full suite; missing/deleted tests or empty regression families also fall back to all. Fresh Windows setup targets Python 3.11 and checks native exit codes without replacing an existing venv.
- Local offline-runner and selector regression scripts passed; previous `0_5_48`, accepted baseline `0_5_0`; full CI/Windows owner PASS pending.

## 0_5_48 — Invalidate disconnected camera observations (candidate; roadmap Update 04 / H03)
- Retire camera delivery before explicit stop, disconnect, reconnect, restart or session replacement. Clear only that source's latest image and increment its observation epoch. Background inference snapshots carry source/mode tokens; invalid or expired predictions are suppressed at completion, API read and virtual-observation forwarding. A mode-generation change invalidates pre-transition predictions, while fresh cached images may still be promoted with their original identity.
- Add lifecycle/inference regression; previous `0_5_47`, accepted baseline `0_5_0`; owner PASS pending.

## 0_5_47 — Preserve ESP cached-frame identity (candidate; roadmap Update 03 / H03)
- Cache one validated immutable CameraFrame per accepted ESP packet, with its original PC receive timestamp and a globally allocated frame ID. Selection, simulation return and background inference reuse the same object; stale caches remain rejected. Ordinary HTTP uploads still allocate and publish new frames. ESP wire sequence remains a transport diagnostic, not the application frame ID.
- Add deterministic cached-frame regression and update multi-camera race fixture. Previous `0_5_46`, accepted baseline `0_5_0`; owner PASS pending.

## 0_5_46 — Guard retired ESP workers (candidate; roadmap Update 02 / H02)
- Guard retired-worker failure, join completion, receive counters/frame metadata and recovery using the worker stop-event identity. Serialize recovery with replacement ESP control commands and recheck ownership around each HTTP stage. Already-issued HTTP calls may finish before replacement control; their stale responses cannot publish state. A frame sink already in progress is not rolled back; cache/source provenance remains Update 03/04.
- Add 11 deterministic worker-retirement cases; previous `0_5_45`, accepted baseline `0_5_0`, owner PASS pending. No firmware, API or signal changes.

## 0_5_45 — Guard cancelled ESP TCP opens (candidate; roadmap Update 01 / H02)
- After a blocking TCP open returns, recheck cancellation, worker event identity, streaming intent and simulation mode before publishing the socket or connection status. The existing finally block closes the returned socket and clears connection status only when it owns the active socket. This prevents a cancelled opener from replacing a new connection. Ordinary open, read and reconnect behavior, firmware, TCP framing, API shapes and signal behavior remain unchanged.
- Add deterministic five-case socket-open regression. Previous `0_5_44`, accepted baseline `0_5_0`; broader retired-worker failure/recovery audit remains Update 02.

## 0_5_44 — Guard late ESP TCP reads during stop and simulation switch (candidate)
- Recheck the worker stop event and current simulation mode immediately after a blocking TCP packet read, before counting or publishing the returned packet. A normal complete packet and ordinary EOF retain their existing behavior. This is a narrow receive-loop boundary fix, not a guarantee of atomic cancellation across every worker or mode-transition path.
- Add six deterministic receive-loop cases, including EOF during a simulation switch. No ESP firmware, protocol, API or signal changes. Previous `0_5_43`, accepted baseline `0_5_0`, owner PASS pending.

## 0_5_43 — Reduce fragmented HTTP camera upload buffering overhead (candidate)
- Aggregate bounded HTTP frame uploads in one `bytearray` instead of accumulating one Python list entry per incoming network chunk, removing redundant per-chunk retention and joining.
- Preserve exactly the 8 MiB limit, 413 error details, JPEG/PNG validation and existing camera API envelope. Add deterministic 4,098-chunk assembly regression; keep ESP TCP fast path untouched. Previous `0_5_42`, accepted baseline `0_5_0`, owner PASS pending.

## 0_5_42 — Keep ESP TCP camera ingestion free of redundant decoding (candidate)
- The V0541 full-image validation also reached the high-frequency ESP TCP frame path through the shared `CameraFrameService.store_upload`, rejecting lightweight transport fixtures and adding unnecessary per-frame decoding.
- Restrict full decodability and pixel-limit checks to `POST /api/camera/frame` using a backward-compatible optional validation flag; retain header-only parsing on the physical TCP stream. Preserve V0541 strict HTTP validation, state-preservation tests and V0540 streaming byte limit.
- Update focused regressions for both pathways; no signal controller, inference API, hardware or 3D changes. Previous `0_5_41`, baseline `0_5_0`, owner PASS pending.

## 0_5_41 — Reject undecodable camera uploads (candidate)
- Require full OpenCV decoding after the existing MIME/header/dimension validation and before updating the latest uploaded frame. Truncated or mislabeled PNG/JPEG bytes can no longer overwrite valid camera data.
- Reject declarations exceeding 16,777,216 pixels before decoding to avoid large memory allocations from small compressed uploads. Keep the existing 8 MiB encoded-byte cap, stable 422 `CAMERA_FRAME_INVALID` envelope and camera/signal/ESP boundaries unchanged.
- Add deterministic valid PNG/JPEG and invalid/truncated/oversized pixel regressions. Previous `0_5_40`, baseline `0_5_0`; CI and explicit owner PASS required.

## 0_5_40 — Bound camera frame upload buffering (candidate)
- Port the tested 0_5_29 `main` streaming limit to this 3D feature branch: accumulate `/api/camera/frame` data only up to the pre-existing 8 MiB size cap instead of calling unbounded `request.body()`.
- Preserve the stable `CAMERA_FRAME_TOO_LARGE` error (413), request IDs, successful upload envelope and existing camera service validation. Add hardware-free streaming/boundary/early-abort regression; leave traffic signal, simulation and physical ESP actuation untouched.
- Previous `0_5_39`, baseline `0_5_0`; feature CI and explicit Windows/owner PASS required.

## 0_5_39 — Align keyboard regression with shared 3D mirror utility (candidate)
- Repair `test_v0523_3d_keyboard.py`: verify `simulationSourcePoint` is exported by `simulation3dMotion.ts` and used by the 3D scene instead of checking for its obsolete inline declaration.
- Keep existing keyboard/focus, region editor and source-mirror checks; no application runtime, hardware, API or signal-control changes. Previous `0_5_38`, accepted baseline `0_5_0`; owner PASS pending.

## 0_5_38 — Restore complete patch documentation (candidate)
- Restore the complete `CHANGELOG.md` and `docs/LOCAL_TESTING.md` after the `0_5_37` write truncated their prior history. Retain the `0_5_37` mirrored 3D signal post fix and all earlier release notes.
- No application behavior changes. Previous `0_5_37`, accepted baseline remains `0_5_0`; candidate awaits normal validation and owner PASS.

## 0_5_37 — Correct mirrored 3D signal post positions (candidate)
- Transform both 3D signal posts with the same camera mirroring used for agents. Camera B/D place them on the vertically mirrored side; Camera C/D mirror them horizontally.
- Add deterministic transform regressions for all four views. No backend/API/signal control/physical camera behavior changes. Previous `0_5_36`, accepted baseline remains `0_5_0`; Windows visual check and owner PASS pending.

## 0_5_36 — Align legacy simulation layout regression (candidate)
- Update `scripts/test_simulation_frame_layout.py` to expect four synthetic vehicle variants introduced in `0_5_35` instead of obsolete car-only.
- Retain source-image background/no-metadata/no-signal drawing assertions; no runtime, styling, camera, signal, API or hardware changes. Previous `0_5_35`, baseline `0_5_0`; CI/owner PASS pending.

## 0_5_35 — Vehicle variety, improved people and pedestrian reentry (candidate)
- Display distinct car, SUV, van and bus models with appropriate proportions, windows, sides, body height and 2D source-image outlines.
- Improve simulated pedestrian skin/hair/clothing details and disable visible CSS backward tweening when they recycle off-screen, as already done for cars.
- Expand deterministic reentry regression and update the legacy car-only source assertion. Keep protected signal policy, camera/API data structure, AI capture, editing and ESP boundaries unchanged. Previous `0_5_34`; accepted baseline `0_5_0`. Owner PASS pending.

## 0_5_34 — Volumetric 3D agents and seamless reentry (candidate)
- Render synthetic cars with elevated cabins, body sides, ends and wheels; render pedestrians upright with head, torso, arms and legs.
- Stop cross-road animation when existing simulator agents recycle off-screen while retaining smooth interpolation during ordinary motion.
- Add deterministic motion regression cases, preserve selected-source simulation, signal policy, ESP, capture and image-coordinate editing. Previous `0_5_33`, accepted baseline `0_5_0`; owner PASS pending.

## 0_5_33 — Hallmark shell regression correction (candidate)
- Fix the V0532 test's overly broad navigation expectation: dashboard redirection occurs only when hiding simulation tools from Simulation Experiments.
- Preserve the V0532 accessible button, styling, backend and simulation logic unchanged. Previous `0_5_32`, accepted baseline `0_5_0`; full CI and owner PASS pending.

## 0_5_32 — Hallmark sidebar control clarity (candidate)
- Replace the implicit clickable brand panel with a native, labeled Simulation tools toggle, preserving the existing navigation handler and pressed state.
- Remove duplicate sidebar version/tagline and repeated legacy eyebrow; keep page descriptions and persistent status/version display. Add a focused shell regression.
- Previous `0_5_31`, accepted baseline `0_5_0`. No API, data, traffic signal, simulation control or physical output changes. Windows/browser validation and owner PASS pending.

## 0_5_31 — Align legacy simulation structure regression (candidate)
- Update the V0418 camera/region source-structure test to assert that one protected signal phase is shared by vehicle and pedestrian movement, replacing obsolete one-argument helper call checks.
- Repair the offline CI failure in `0_5_30`; retain its runtime optimization without modification. Previous `0_5_30`, accepted baseline `0_5_0`; owner PASS pending.

## 0_5_30 — One protected phase snapshot per simulation step (candidate)
- Advance vehicles and pedestrians from the same signal phase snapshot in each 50 ms simulator substep, eliminating a duplicate stateful controller query per substep.
- Add an exact call-count regression, preserve existing vehicle queue/pedestrian WALK safety tests, and clarify simulation ownership and acceptance documentation.
- Previous `0_5_29`, accepted baseline `0_5_0`. No API, settings/data schema, inference, 3D, ESP, virtual conflict-interlock or physical-output changes. Performance improvement is not benchmarked; owner PASS pending.

## 0_5_29 — Simulation camera mirror-render optimization (candidate)
- Reuse the existing BGR render for mirrored simulated camera B/C/D views; avoid decoding the same PNG repeatedly per simulation tick.
- Clear the bounded render cache on simulation reset, stop and resume; add pixel-equivalence and no-decode regression; document feature-branch validation.
- Previous `0_5_28`, baseline `0_5_0`. APIs, 3D scene, real ESP transport, virtual signal safety and disabled physical actuation unchanged; owner PASS pending.

## 0_5_28 — Reconnect-safe emergency evidence (candidate)
- Use strictly increasing per-source frame timestamps for emergency evidence after camera counter resets; reject duplicate or older samples.
- Extend deterministic emergency-priority regression for reconnect positives, reconnect negatives and replay. Previous `0_5_27`, baseline `0_5_0`; protected virtual transitions and physical actuation unchanged.

## 0_5_27 — Late inference shutdown guard (candidate)
- Skip caching a detection that finishes after stop has already been signaled; avoid crosswalk publication on shutdown.
- Add a deterministic threaded regression for late inference with bounded join and preserve the existing restart guard. Previous `0_5_26`, baseline `0_5_0`; no physical output changes.

## 0_5_26 — Inference worker lifecycle guard (candidate)
- Retain the worker reference after a timed-out stop to prevent overlapping inference threads on quick restart.
- Add deterministic timed-out join, restart and cache-cleanup regressions; no changes to camera API, traffic signals or physical actuation. Previous `0_5_25`, baseline `0_5_0`.

## 0_5_25 — Per-camera inference diagnostics (candidate)
- Add source-frame age/freshness and measured inference latency to the existing per-camera API and AI Preview.
- Add deterministic source-isolation/stale diagnostics regression; no changes to hardware actuation or signal decisions. Previous `0_5_24`, baseline `0_5_0`.

## 0_5_24 — Multi-camera source freshness (candidate)
- Reject same/older per-source frame timestamps and avoid inference-cache reuse after camera frame-number reset.
- Reuse existing global camera registry, inference model and crosswalk mappings. Previous `0_5_23`, baseline `0_5_0`.

## 0_5_23 — Keyboard-accessible 3D controls (candidate)
- Add keyboard orbit, tilt, zoom and reset; visible focus indicator; preserve existing 3D region and camera behavior.
- No changes to signal-control or hardware paths. Previous `0_5_22`, baseline `0_5_0`.

## 0_5_22 — Network fail-closed virtual interlock (candidate)
- Hold conflicting virtual signals red when a connected controller is unavailable; sanitize contradictory phase/lamp states to all red.
- Add deterministic absent-neighbor and invalid-signal regression. Previous `0_5_21`; baseline `0_5_0`.

## 0_5_21 — Same-source emergency confirmation (candidate)
- Require two time-separated ambulance-positive frames from the same source before a one-hop emergency request. Add adversarial two-camera regression.
- No change to physical output or protected phase timing. Previous `0_5_20`; baseline `0_5_0`.

## 0_5_20 — Candidate CI automation
- Introduce Windows GitHub Actions checks for Python compile, structure, offline regressions, frontend typecheck and build.
- No physical camera, live server or local Windows acceptance claimed. Previous 0_5_19, baseline 0_5_0.

## 0_5_19 — Confirm emergency priority from distinct fresh frames

- Bind ambulance confirmation to source ID, frame number, frame timestamp and active model; require two unique fresh positive frames separated by at least one second in frame time.
- Prevent repeated polls, unrelated camera updates and synchronized views from creating confirmation; clear evidence after unavailable/stale/incomplete coverage, model changes, or newer negative frames.
- Preserve bounded opt-in virtual route requests, protected signal transitions, Network conflict checks and disabled physical actuation. Candidate on `feature/interactive-3d-simulation`; previous `0_5_18`; accepted baseline remains `0_5_0`; Windows/hardware validation and owner PASS pending.

# Changelog

## 0_5_18 — Fix nullable 3D status scene references

- Read the phase countdown and agent totals from `activeScene`, which is already checked for null in the status panel.
- No changes to rendering, simulation, backend APIs, camera inputs, signal policies, or physical outputs. Candidate on `feature/interactive-3d-simulation`; accepted baseline stays `0_5_0` pending validation and owner PASS.

## 0_5_17 — Fix 3D scene regression test ordering

- Compare live simulation scene coordinates to the service state immediately after creating the snapshot, before requesting another frame that advances moving agents.
- Test-only repair. No application runtime, API, signal policy, source image, dataset, or 3D rendering changes. Candidate on `feature/interactive-3d-simulation`; accepted baseline remains `0_5_0` pending Windows/physical preview validation and owner PASS.

## 0_5_16 — Update outdated Crosswalk 3D structure assertion

- Repair the legacy Crosswalk Region Editor regression expectation for the removed 2D simulation MJPEG URL: verify selected 3D source, aligned region edit mode and preserved physical ESP MJPEG preview.
- No application runtime, API, AI inference, region geometry, frontend rendering, dependency or traffic-signal changes. Prior candidate `0_5_15` stopped at this stale test; `0_5_16` remains a feature-branch candidate pending full Windows checks and owner PASS.


## 0_5_15 — All live simulated camera previews in 3D

- In addition to Camera Settings and Camera Sources, replace Crosswalk paired simulation images, Crosswalk Region Editor simulated image, Camera AI Preview synthetic image, and Dataset Capture synthetic image with the same interactive 3D renderer.
- Use actual current simulation agents, signal phases and source-specific mirror transforms. Project existing detector boxes and regions onto the synthetic world plane; give the Region Editor a 3D orbit preview plus coordinate-aligned top-view editing to retain accurate draggable vertices and saved 2D-frame polygons.
- Keep real ESP images, canonical 2D PNG/MJPEG, dataset training captures and manual labels, Network controllers and safety logic intact. No additional dependencies or new model capabilities. 0_5_15 remains an unaccepted feature-branch candidate pending Windows tests and owner PASS.

## 0_5_14 — Repair incomplete 0_5_13 release bundle

### Same-candidate continuation: Network movement conflict interlock

- Preserve previously implemented camera-to-crosswalk inference routing; configure explicit per-connection vehicle/pedestrian movement conflicts and persist them with the Network layout.
- Simulation-only coordinator pauses blocked independent crosswalk phase clocks, projects virtual all-red holds, requires a 2 s conflict-clearance gap, preserves protected local transitions, and prevents simultaneously conflicting published green movements.
- Network shows coordinated hold/priority reasons and countdowns. Directed emergency-route requests require configured conflicts and expire if unserved. No physical actuation, cross-camera identity tracking, or certification.


- Complete the release metadata required by the project structure gate after the previous patch's TypeScript null-safety fix: add `docs/PATCH_0_5_14.md`, synchronize Start Here, Local Testing, Test Ready Checklist and the frontend shared version constant.
- Keep the `CameraDetectionView` optional-resolution fix from `0_5_13`; no further runtime code, camera inference, controller safety, APIs, or hardware changes.
- Previous candidate `0_5_13`; accepted baseline `0_5_0`. Full Windows structure/typecheck/build/startup and owner PASS pending.

## 0_5_13 — Camera AI Preview nullable status fix

- Fix the frontend TypeScript nullability error in CameraDetectionView by reading optional resolution dimensions through `cameraStatus?.resolution` when the selected camera has no status yet.
- Preserve fallback frame dimensions (1280 × 720), preview rendering, inference/API contracts, and signal-control behavior. No backend or firmware changes.
- Focused strict TypeScript nullable-status validation passed; full Windows frontend typecheck, runtime smoke test, and owner PASS pending. Previous candidate `0_5_12`; accepted baseline `0_5_0`.

## 0_5_12 — Automatic camera detections for independent crosswalk controllers

### Same-candidate follow-up: directional emergency route

- A saved Network link may specify one opt-in source→destination or destination→source emergency vehicle route; links default Off. Ambiguous multiple outgoing or incoming routes are rejected.
- Two separate fresh inference frames showing an ambulance class over ≥1 s request virtual vehicle priority at the next crossing. Its own controller may extend vehicle green by up to eight seconds within existing bounds, while retaining mandatory pedestrian, amber and all-red phases.
- Network displays configured direction and active origin/reason. This uses the existing camera-to-crosswalk observation pipeline for simulated or ESP-video virtual preview. No physical actuation or measured traffic-jam reduction is claimed.


- Connect the existing background per-camera AI inference worker to saved Crosswalk Side A/B camera assignments; continuously route fresh detections into the correct independent simulated signal controller even when Network is closed.
- Count object classes inside camera-specific polygons using the detection's bottom-center point, assigning each detection to at most one region per camera. Combine Side A/B region counts by per-class average when both cameras are recent and synchronized; otherwise use a single available view and mark partial coverage. Defined-only-on-one-side regions remain one-sided.
- Route each crosswalk's class counts into both physical region ID and crosswalk-qualified scenario keys, making its existing ranked class-based adjustment rules observable without mutating other controllers. Show camera coverage and region class counts on Network and make saved Crosswalk regions selectable in Live Signal Adjustments.
- Immediately withdraw observations when the camera/model becomes unavailable or stale. Valid empty frames remain valid zero-object counts. Prevent untyped region occupancy from being falsely interpreted as waiting pedestrians, crossing pedestrians, or vehicle queues. Preserve decimal averages in scenario class threshold checks.
- Runs software-only simulated controllers from simulated cameras and virtual preview controllers from fresh real ESP camera AI. No new real signal actuation, no crosswalk conflict-coordination, and no fabricated wheelchair/ambulance classification. Candidate `0_5_12`, previous `0_5_11`, accepted baseline `0_5_0`. Python/Windows runtime validation and owner PASS pending.


## 0_5_11 — Separate crosswalk signal controllers

- Add one independent simulation-only SignalRulesService runtime per saved crosswalk, using existing central timing/rule configuration but isolated controller state and separate history paths.
- Add read-only GET /api/traffic/crosswalk-signals with keyed crosswalk states, neighbors and coordination capability flags; Network now renders each crosswalk's own simulation signal instead of copying the selected-source controller.
- Add internal observation and Test-mode input hooks for future camera-to-crosswalk mapping. No automatic camera observation injection, neighbour phase coordination or physical actuation; Network edges currently identify adjacency only.
- Preserve legacy global signal controller/camera simulation behavior, controller constraints and settings APIs. Current candidate 0_5_11; previous 0_5_10; accepted baseline 0_5_0. Windows verification pending.


## 0_5_10 — Network signals and adjustable timing/rules (partial)

- Add Traffic Light Settings page for default vehicle, amber, pedestrian WALK/CLEAR and protected all-red phase durations, persisting through the existing signal-rules API with maximum/minimum guards.
- Add Live Signal Adjustments page with disabled-by-default templates for ambulance-class priority requests/vehicle green extensions, wheelchair-class pedestrian extensions, crowd/vehicle queue thresholds and near-end pedestrian clearance protection. These reuse ranked scenario configuration, model/region-dependent observations and the shared simulation controller; no independent controller created.
- Extend the existing scenario evaluation metrics with `phase_remaining_seconds` to combine crossing occupancy and an end-of-clearance threshold. Hold and extension actions remain bounded by safety minima, phase caps and cycle cap.
- Enhance Network crosswalk cards with small vehicle/pedestrian signal heads, source-scoped live simulation state, countdowns, adjustment names, and **advisory-only** notices on directly linked neighbours. Non-observed crosswalks explicitly display unavailable—not copied phases or claimed coordinated holds.
- **Not implemented:** per-crosswalk signal controllers, verified conflict-movement topology, actual neighbour phase adjustments, real emergency preemption or flashing-green public-road control. Cross-camera class detection to legacy active scenario-zone binding is not guaranteed. No ESP/physical signal commands changed.
- Candidate `0_5_10`, previous `0_5_9`, accepted baseline `0_5_0`. Focused tests added; full Windows/typecheck/smoke/hardware validation and owner PASS pending.


## 0_5_9 — Global AI Models and multi-camera preview

- Place Traffic above the AI navigation group and remove the Settings page from navigation, preserving the existing runtime-settings API and old saved settings.
- AI Models now imports new local .pt weights (up to 200 MiB, no overwrite), lists/loads/defaults/unloads/deletes models, prevents deletion of the active model, and saves one global confidence threshold and an inference-interval slider (100–2000 ms).
- Run a single active model sequentially against the newest available frame from each saved active ESP or saved simulated camera via a background worker. Keep per-camera results and reject stale frames without accumulating a processing queue; actual interval is best-effort and may be slower if inference saturates the PC.
- Redesign Camera AI Preview to select any registered camera without changing the shared camera selection, show the latest selected-camera feed and labeled detection boxes, overlay existing crossing region polygons with Side A/B geometry, and display per-class per-region current counts outside the image.
- Leave legacy selected-source traffic analytics/tracking/network overview, camera dataset capture, firmware, signal safety, and physical control unchanged. Multiple preview results do not establish cross-camera identity fusion, live multi-junction control, or certified safety.
- Candidate `0_5_9` (previous `0_5_8`); accepted baseline `0_5_0`. Windows regression/build/smoke and owner PASS pending.



## 0_5_8 — AI workspace and direct Network edge connections

- Move Camera Settings and Camera Diagnostics above the new AI sidebar group.
- Group Camera AI Preview (existing live inference page) and AI Models (existing model registry) under **AI**, keeping original internal page IDs and API routes. The preview shows actual camera inference with detection boxes, class filters and a clear no-camera state instead of presenting synthetic fallback detections. The preview no longer auto-loads models; model loading is explicitly controlled through AI Models. AI Models retains loading/defaulting/deleting models and adds unloading and persistent default inference confidence using existing runtime settings.
- Replace Network's connection dropdown form with direct pointer dragging between numbered edge labels. Provide a live preview line, valid target highlighting, keyboard edge-to-edge alternative and cancel-on-invalid-release; draw saved connections from the actual label centers. Keep drag-to-reposition on crossing titles and existing network persistence/validation.
- No backend, hardware firmware or physical traffic controller changes. The original selected-source-only inference, safe signal behavior and Crosswalk configuration schema remain intact.
- Candidate `0_5_8` (previous `0_5_7`), accepted baseline remains `0_5_0`. Full Windows regression/typecheck/build/smoke and owner PASS pending.


## 0_5_7 — Crossing-first Network workspace

- Place Crosswalks above Network in the Traffic menu and rename Junction Network to Network, retaining its internal route for compatibility.
- All saved crossings appear automatically as crossing boxes; save crossing positions and numbered-edge connections through optional crosswalk-network metadata in existing atomic Crosswalk persistence.
- Show assigned camera connection/stream health for each crossing and selected-source-only detector region counts. No fabricated observations, simultaneous inference, vehicle transfers or physical signal commands.
- Preserve current junction/source topology and editors in a collapsed advanced section. Existing intersections.json, APIs and signal safety remain unchanged.
- Extend focused crosswalk network validation/persistence regression. Candidate `0_5_7`; previous `0_5_6`; owner-accepted baseline remains `0_5_0`. Windows full-suite PASS pending.


## 0_5_6 — Shared physical regions with independent A/B polygons

- A new Region Editor region is a single named physical area shown on both camera sides; dragging handles on one side changes only that side's polygon. Its internal ID is hidden from users.
- Preserve the validated schema-1 crosswalk API, current Save regions button, original `vertices` fallback, and previously saved one-sided regions. No automatic merging of old unrelated region IDs.
- Per-frame detector counts keep independent camera-region IDs and expose a shared physical-region ID; do not sum A/B counts as distinct people/vehicles or imply simultaneous inference.
- Extend deterministic persistence/counting regressions and update historical frontend assertions for shared selection across camera sides.
- Candidate `0_5_6`; previous `0_5_5`, owner-accepted baseline remains `0_5_0`. Windows startup, full regression and visual acceptance pending.


## 0_5_5 — Align camera/region regressions with current implementation

- Update Camera Settings structure assertions to the existing paired simulation save call, concealed simulator controls, filtered saved-camera list and effective ESP-only form state.
- Update the historical V0418 Region Editor assertions for Side A/B camera switching that also clears the previous selection.
- Preserve all application/firmware/backend runtime files, camera pairing, region IDs, counts and signal logic unchanged. Candidate after failing 0_5_4 regression; accepted stable baseline remains `0_5_0`. Windows full acceptance pending.


## 0_5_4 — Camera-scoped counting regions

- New regions are independently defined on Side A or B, including polygon, display label and backend identifier. Legacy shared regions remain readable.
- Active-source detections are counted per class and region without changing signal control. Save regions reuses existing storage. Candidate; Windows PASS pending.


## 0_5_3 — Fix V052 release consistency

- Repair current version label and required candidate documents so the structure/version gate can proceed.
- No Region Editor, backend, camera or signal runtime changes. Accepted baseline remains `0_5_0`; Windows acceptance pending.


## 0_5_2 — Save from Region Editor

- Add Save regions in the Region Editor, using the existing Crosswalks save API and existing unsaved-change/busy states.
- Do not change region geometry, existing shared-camera model or counting logic. Camera-specific region identities and counting semantics require an explicit schema/backend migration and are not yet implemented.
- Candidate `0_5_2`, accepted baseline `0_5_0`; Windows tests pending.


## 0_5_1 — Hide simulation tools behind brand toggle

- The top-left AI Traffic Light panel toggles simulation options throughout the PC app (click, Enter or Space). They are concealed by default.
- Hide Experiments navigation, simulated-camera creation/previews and simulation controls; keep real ESP camera controls and truthful active-source state.
- UI-only candidate. Existing camera source, signal controller, APIs and stored data are unchanged. Stable baseline `0_5_0`; Windows tests and owner PASS pending.


## 0_5_0 — Owner-accepted stable release

- The owner confirmed PASS for candidate `0_4_24` and explicitly requested the next stable version; promote the accepted code as stable `0_5_0`.
- Preserve the tested Crosswalk layout (Side A and Side B side-by-side selectors and source states), translucent selected/unselected region polygons, simulation camera pairing, camera selection and existing safety constraints.
- This is a version and release-documentation milestone only. No application-code, firmware, API, data-model, dependency or signal-control logic changes.
- Previous version: `0_4_24`. Accepted stable baseline: `0_5_0`. The owner may run the normal Windows update/test runner to verify the updated release label; no additional test run is implied by the promotion.


## 0_4_24 — Consolidate Crosswalk camera-side rows

- Crosswalk layout shows Side A and Side B as two equal-width columns above the schematic, each containing the existing camera selector and the corresponding live camera state.
- Shorten the selector headings to `Side A` and `Side B`; remove duplicate status rows and the bottom Side B selector. Stack camera columns on narrow screens.
- Keep camera assignment, missing-source warnings, simulation preview, region editing, saved data, translucent region styling and traffic behavior unchanged.
- Extend the existing Crosswalk frontend regression to protect one selector per side, side-by-side placement and responsive stacking. Previous candidate `0_4_23`; accepted baseline `0_4_14`. Windows acceptance pending.


## 0_4_23 — Restore translucent Crosswalk region fills

- Correct the Crosswalk Region Editor's opaque/empty appearance: normal polygons receive a 10%-opacity mint tint; selected polygons receive a 22%-opacity pale cream tint. Both show the camera feed through the polygon.
- Remove the redundant polygon SVG `fill="none"` presentation attribute; retain the brighter, fully opaque 6px pale-yellow dashed selected stroke, existing handles, coordinate mapping, saved geometry and camera-side controls.
- Match the tint in the hidden legacy region editor while preserving its 7px selected outline. Live AI/simulation region overlays stay unfilled; dataset boxes, inference and signal logic are unchanged.
- Update affected region regression expectations (V0417/V0418/V0420/V0422) to check the active translucent contract rather than the superseded no-fill contract.
- Previous candidate `0_4_22`; passed stable baseline `0_4_14`. Windows GUI appearance, frontend build, startup and live smoke await owner PASS.


## 0_4_22 — Responsive panel/text alignment and clear selected-region outlines

- Standardize responsive typography and wrapping in existing shared `styles/base.css`, `styles/layout.css` and `styles/components.css`: fluid headings/metric figures, text wrapping in boxes/buttons/status pills, flexible page/panel headers, and status bars that grow rather than clip.
- Remove ellipsis-based truncation from Junction Network camera IDs, source descriptions and link labels. Allow Simulation Experiment scenarios, rule descriptions and tabs to wrap, and use page scrolling on short desktop screens instead of concealing results. Allow Signal Control scenario descriptions to wrap.
- Keep selected and unselected region interiors completely transparent. Selected Crosswalk polygons use an opaque pale-yellow `#FFF5C7` 6px dashed outline (7px in hidden legacy editor), with vertex handles unchanged.
- Align historical V0417/V0418/V0420 tests to the revised selection contract and add `test_v0422_responsive_layout.py`. Preserve Live AI overlays, dataset boxes, camera switching, V0421's second simulation-camera pair, signal safety logic and stored data unchanged.
- Previous candidate `0_4_21`; accepted stable baseline `0_4_14`. Windows frontend build, backend smoke and visual validation remain pending.


## 0_4_21 — Second saved simulation camera pair

- Add simulation camera Pair 2 (`simulation_camera_c` and `simulation_camera_d`) alongside the existing Pair 1 (`simulation_camera` and `simulation_camera_b`).
- Extend the existing saved-camera manager to persist and delete each pair separately. Switching between the two pairs and physical cameras reuses the existing selection service, keeping the active stream and simulated-mode transitions consistent.
- Extend the existing camera renderer's per-source frame views and MJPEG preview routing: Pair 2 shows a distinct horizontally reflected view of the existing synthetic scene; its two sides are vertically mirrored. Both pairs share one simulation clock and safety policy, **not** separate intersections.
- Camera Settings now enables `Add second simulation pair` after Pair 1 exists, enforcing the existing 12 saved-camera limit. Existing Crosswalks `Assign simulation pair` remains backward-compatible with Pair 1, while its camera pickers can select Pair 2 IDs.
- Add a dedicated structure test, extend camera-frame and remote-camera-manager regressions for four simulation views, persistence, pair isolation and safe deletion.
- No new dependencies or separate camera services; previous candidate `0_4_20`, owner-accepted stable baseline `0_4_14`. Windows backend, frontend build and live acceptance pending.


## 0_4_20 — Subtle selected-region highlight

- Keep unselected polygons fully clear; when selected, use a pale cream `rgba(255, 246, 210, 0.22)` fill. Camera frames remain visible through the 22% highlight.
- Preserve the thicker dashed warning-colored outline and draggable numbered vertices. Apply equivalent selected styling in the hidden legacy region editor.
- Remove the Crosswalk Region Editor's unconditional SVG `fillOpacity={0}` presentation attribute, which prevented selected translucent fills from appearing. Continue using the normal SVG `fill="none"` plus state-specific CSS.
- Update the historical V0417/V0418 transparency assertions and add `test_v0420_selected_region_highlight.py` to check opacity range, unselected transparency, borders and camera compatibility.
- No geometry, region/camera data, APIs, simulator, traffic timing, dependency or other styling changes. Previous candidate `0_4_19`; owner-accepted stable baseline remains `0_4_14`. Windows build and live smoke pending.


## 0_4_19 — Fix duplicate CSS selector regression lookup

- Fix the V0418 first-run `test_v0418_camera_region_ui.py` failure by inspecting all declarations of `.camera-status-entry`. The pointer cursor is present in the original CSS block; a later background-only rule was incorrectly selected by the test helper.
- Add a two-rule fixture asserting that the helper sees both layout and background declarations. Check the remaining camera, region and simulation structure assertions against the current sources.
- Keep the complete pre-V0418 source archive and add a reminder to avoid assuming CSS selectors occur only once.
- No runtime application, CSS, backend, traffic, camera or API changes. Previous candidate `0_4_18`; accepted stable baseline remains `0_4_14`. Windows regressions/build/live smoke pending.


## 0_4_18 — Camera selection, cleaner simulation and region controls

- Allow direct selection of saved cameras by clicking their cards, reusing the existing `chooseSavedCamera` path. Keep selection, busy and keyboard-focus indicators accessible.
- Remove all text banners, `STOP` labels, vehicle/pedestrian signal heads and synthetic buses from the simulated camera **image**. Cars, pedestrians, road/crossing geometry and the separate signal-policy logic remain.
- Replace the Crosswalk Region Editor camera-side dropdown with two accessible Side A / Side B toggle buttons; preserve camera preview and region geometry.
- Explicitly mark SVG polygons as unfilled in addition to existing CSS, with warning-colored selected outlines and four draggable vertex handles unchanged.
- Center status-pill text horizontally and vertically, addressing the `Simulation active` alignment issue.
- Store the six complete pre-patch affected source files in `docs/backups/V0417_PRE_V0418_CODE.md`, including failure-prevention notes and the immutable V0417 Git reference.
- Add a focused UI/renderer regression and update the historical simulation-frame layout test. Previous candidate `0_4_17`; accepted stable baseline `0_4_14`. Windows build, smoke and visual validation pending.


## 0_4_17 — Transparent region polygons

- Remove polygon interior fills from the Crosswalk Region Editor, including selected regions, so camera frames remain unobstructed. Unselected regions retain mint outlines; selected regions retain transparent interiors but are highlighted by thicker, contrasting warning-colored dashed outlines and draggable numbered vertices.
- Apply fully transparent interiors to Live AI region overlays, simulation/mock regions and the retained legacy region editor. Keep strokes, labels and selection distinctions.
- Leave Dataset Review object-label boxes unchanged; only region polygons are affected.
- Add a focused CSS/interaction regression. No geometry, data storage, camera, signal controller, API or dependency changes.
- Previous candidate `0_4_16`; owner-accepted baseline stays `0_4_14`. Local Windows build, smoke and visual acceptance pending.


## 0_4_16 — Remove empty Zones page; standardize Regions terminology

- Remove the empty Traffic → Zones page, navigation entry, route and unused page component. Crosswalk Region Editor remains the place to define crosswalk regions.
- Display `Region/Regions` rather than `Zone/Zones` in Live AI, Signal Control, Traffic Analytics, feature descriptions, mock labels and the preserved hidden legacy editor.
- Preserve the legacy `zone_editor` route for compatibility and leave stored `zone_id`, `zones` JSON, backend `/api/zones` routes and historic IDs unchanged. This is a UI naming change, **not** a storage/API migration.
- Replace the historic navigation test's empty-Zones requirement and add focused terminology and compatibility regression checks. No camera, simulation, traffic-signal or backend behavior changes.
- Previous candidate `0_4_15`; owner-accepted baseline remains `0_4_14`. Windows frontend typecheck/build, regressions and live smoke pending.


## 0_4_15 — Slightly darker dark-mode canvas

- Darken the shared dark application canvas from `#4D4E61` to `#444557` while retaining the approved mint `#57FFED`, sidebar, controls, panels and light theme.
- Align the existing palette and invalid-token regression fixtures with the new canvas value. No API, hardware, camera, traffic, layout or dependency changes.
- User accepted `0_4_14` as the latest stable baseline; `0_4_15` is a candidate awaiting Windows startup and visual confirmation.


## 0_4_14 — Remove stale historical navigation assertions

- Repair the V0413 first-run `test_v0409_palette_layout.py` failure: the test still required `color-nav-heading-surface`, a token intentionally removed by the quiet-navigation redesign.
- Keep V0409's slate/mint color and Junction Network layout checks, but remove duplicated navigation appearance assertions. V0413's dedicated quiet-navigation regression now owns the sidebar's current visual contract.
- No runtime application, sidebar CSS, backend, traffic, camera or dependency changes. Previous candidate `0_4_13`; accepted baseline `0_4_0`; Windows typecheck/build and live smoke pending.


## 0_4_13 — Quiet slate sidebar navigation

- Replace sidebar section title boxes and thick mint bars with small, muted uppercase headings and subtle horizontal dividers.
- Use a neutral slate background and brighter text for the active navigation row instead of teal selection fill, mint left bar and trailing dot; make hover subtle and keep 6px corners.
- Reserve mint for functional control selections and keyboard focus. The separate sidebar brand panel remains, and the light theme uses matching neutral navigation roles.
- Add navigation-specific light/dark contrast checks and update historical styling regressions. No routes, APIs, dependencies, simulation, camera, junction or traffic changes. Previous candidate `0_4_12`; accepted stable baseline `0_4_0`.


## 0_4_12 — Junction card regression selector alignment

- Fix `test_v0411_junction_card_layout.py` to inspect the last matching CSS selector rule instead of its earlier occurrence in a grouped selector list. This resolves the reported false assertion for `.junction-node-alerts` alignment.
- Add a synthetic grouped-selector regression so the helper continues checking the intended standalone declaration.
- No Junction Network UI, CSS, geometry, camera, topology or signal behavior changed. Previous candidate `0_4_11`; accepted baseline `0_4_0`. Windows frontend build and smoke testing still pending.


## 0_4_11 — Junction card title/content/edge layout and responsive text

- Reorganize each Junction Network node into a full-width draggable title bar (junction name, ID, current active status) and a centered information area for traffic load, camera count, phase and alerts.
- Place numbered edge buttons 1–4 in a 3×3 content grid: top, right, bottom and left around the information area, never over the title bar.
- Replace fixed card insets with fluid card width and container-relative text sizing; allow labels, statuses and IDs to wrap, and let card height grow to fit available content.
- Keep existing drag offset, edge-to-crosswalk assignment, selection and data/API logic unchanged. Extend card-layout regressions and align earlier layout tests.
- Previous candidate `0_4_10`, accepted stable baseline `0_4_0`; owner Windows build and visual acceptance pending.


## 0_4_10 — Camera Settings TypeScript typecheck repair

- Remove two unreachable `newCameraType === "simulation"` comparisons inside an ESP-only branch in Camera Settings, fixing the two reported `TS2367` frontend errors.
- Keep Save/Connect disabled when busy, streaming or ESP configuration is incomplete. Leave simulation-pair creation, camera selection and transport behavior unchanged.
- Add targeted regression assertions to prevent comparisons against `simulation` inside the narrowed ESP-only form.
- V0409's slate/mint visual design remains unchanged. Previous candidate `0_4_9`; accepted baseline `0_4_0`. Windows TypeScript build/startup pending.


## 0_4_9 — Slate/mint design alignment

- Use the approved `#4D4E61` dark canvas with coordinated opaque sidebar (`#414354`), brand/header boxes (`#333648`), panel (`#55576A`), nested surface (`#5A5C70`), input (`#47495B`) and selected (`#2F585A`) color roles.
- Retain `#57FFED` dark mint emphasis and accessible `#006F66` light mode. Rebalance text, borders, semantic states and vehicle/pedestrian chart colors against the new surfaces.
- Place the sidebar title in a distinct solid panel; give each navigation group a bordered heading strip while preserving active page dots and mint selection.
- Move Junction Network 1–4 edge controls from outside the card into a reserved interior perimeter without covering junction data; retain edge mapping, drag handling and selection.
- Update palette, contrast and Junction Network layout regressions. No dependencies or backend/camera/signal logic changes. Previous candidate `0_4_8`; accepted baseline `0_4_0`.


## 0_4_8 — Safe recognition of system-Python Uvicorn reload child

- The user's Windows process trace shows the port-8000 Uvicorn child (system Python) under the project's virtualenv Uvicorn launcher. Extend the runner's identity check to verify this direct relationship, the expected application and port, and the parent's reload command before stopping the backend tree.
- Preserve refusal to terminate unrelated Python processes and keep the hosting PowerShell window outside the terminated process tree.
- Add a mocked Windows PowerShell process regression for the reported child/parent layout, multiprocessing workers, and unrelated-port-owner rejection.
- No frontend behavior, backend services, dependencies, camera transport or traffic controller changes; accepted stable baseline remains `0_4_0`.


## 0_4_7 — Safe Windows backend restart

- Recognize Windows Uvicorn `--reload` worker processes by matching the project's virtualenv Python and verifying their Uvicorn parent, addressing unrecognized `python.exe` listeners on port 8000.
- Stop the Uvicorn tree without terminating the containing PowerShell host; preserve refusal to terminate unrelated process owners.
- Extend the existing updater safety regression to guard worker ancestry and process-tree boundaries.
- No dependencies, frontend runtime, backend API, camera, intersection or signal-controller changes. Previous candidate `0_4_6`; passed stable baseline `0_4_0`; Windows validation pending.


## 0_4_6 — Junction Network regression assertion repair

- Updated two stale Junction Network regression checks: verify the current simulation/physical-camera mode label and the actual primary-camera assignment control, instead of requiring removed instructional text.
- No application runtime, theme, camera registry, topology, or traffic signal changes. Previous candidate `0_4_5`; owner-accepted baseline `0_4_0`. Windows re-test pending.


## 0_4_5 — Mint accent and visible selection states

- The dark-theme primary accent is `#57FFED`; the light theme uses contrast-safe `#006F66`. Related hover, pressed, secondary, focus and selected-surface roles share the teal family.
- Selected navigation, active tabs, segmented/toggled choices, selected crosswalks, camera status, dataset items and junction edge choices gain a colored dot, bar or ring alongside the selected fill.
- Crosswalk schematic guide/camera marks use a legible dark-teal scene token rather than obsolete blue literals.
- ARIA current/pressed/selected attributes expose existing UI states; the Live AI visibility filter styling reflects checked settings.
- No new dependencies, camera transport, intersection behavior or signal safety changes. Previous candidate `0_4_4`; stable accepted baseline `0_4_0`.


## 0_4_4 — Dark theme structure-validator repair

- Replaced the obsolete `#121212` dark-canvas assertion with a check for a valid hexadecimal dark-base token and a canvas that references it.
- Extended the existing visual regression to ensure the structure guard accepts the V0403 palette and rejects an invalid dark-base value.
- No runtime, CSS palette, camera, topology, data or signal-control changes. Previous candidate `0_4_3`; owner-accepted baseline `0_4_0`.


## 0_4_3 — Shared UI design refinement

- Rebalanced the semantic blue/slate light/dark tokens for Fluent-style neutral surfaces, readable foreground hierarchy and meaningful status colors.
- Standardized 40px controls, clearer focus indicators and stronger field strokes, 4px-based spacing, page headings, navigation selection and restrained panel depth.
- Removed active-page hardcoded dark form/chart/list palettes from Camera-related region editing, dataset review, analytics, AI detection and Settings while keeping dark media overlays separate.
- Clarified analytics segmented selection and simulation tab appearance, keyboard navigation, labels and selected state.
- Added focused static style, tab and WCAG contrast regression checks; no new dependencies or backend/runtime behavior.
- Previous candidate `0_4_2`; stable accepted baseline `0_4_0`. Owner acceptance pending.


## 0_4_2 — Crosswalk regression alignment

- Replaced the stale single-simulation-camera static assertion with checks for both mirrored source IDs, assigned paired cameras, and numbered Crosswalk edges.
- No runtime behavior changes. Stable baseline `0_4_0`; owner PASS pending.


## 0_4_1 — Crosswalk edges, mirrored simulation pair, navigation and junction UX

- Display direction-neutral 1–4 labels on the Crosswalk schematic; assign an existing mirrored simulated camera pair to sides A/B.
- Create and persist two simulated camera profiles atomically; Side B is a vertical flip of the same deterministic scene, with individually selectable previews.
- Move Junction edge controls outside the node card and preserve pointer-to-node offset during dragging.
- Mark Dashboard, Camera Settings and Crosswalks stable; hide legacy Camera Sources/Zone Editor navigation, retain their routes, and add an intentionally blank Zones page.
- Simplify page titles, subtitles and redundant status labels. No new signal-control behavior; dual-camera inference is not enabled.
- Passed baseline: `0_4_0`. Owner acceptance pending.


## 0_4_0 — Owner-accepted stable release

- Owner confirmed candidate `0_3_27` PASS and explicitly approved promotion to stable `0_4_0`.
- Functional code is unchanged; `0_4_0` is the new accepted baseline.


## 0_3_27 — Camera Settings preview regression assertion repair

- Updated the Camera Settings static regression to assert both the selected simulated preview and the explicit physical ESP-only guard; removed the obsolete exact ESP-only expression inherited from V0325.
- No runtime, camera transport, topology, backend, hardware or firmware changes. Owner validation remains pending, and passed baseline stays `0_3_11`.


## 0_3_26 — Numbered junction edges and saved simulation camera

- Junction edges use direction-neutral labels 1–4; new topology lines record source and destination edge identifiers in existing approach fields.
- Preserved legacy cardinal edge keys in saved crosswalk assignments for backward compatibility.
- Camera Settings New Camera can register one simulation camera with no IP or ESP socket; the shared simulated scene is reused and appears in Crosswalk camera assignments.
- Physical ESP transport and signal-control behavior remain unchanged. Passed baseline `0_3_11`; owner PASS pending.


## 0_3_25 — Startup regression assertion repair

- Replaced two brittle camera-settings/crosswalks static assertions that assumed adjacent entries in the shared camera polling page list. Each regression now checks that its required page identifiers are present, independent of ordering.
- No application, transport, API, hardware, configuration or runtime behavior changed. Owner-confirmed baseline remains `0_3_11`; full Windows startup/owner acceptance is pending.
## 0_3_24 — Junction edge labels and crosswalk links

- Added N/E/S/W labels at all four sides of every junction map card and clickable edge selection.
- Added assignment of a saved crosswalk to each selected edge in the existing Junction Network inspector, with clear/remove, missing-reference warnings and duplicate prevention.
- Saved edge mapping with the existing junction network JSON (schema version 1), filling empty mappings when opening older saves.
- No new signal logic, road control or inference; owner-confirmed baseline stays `0_3_11`.

## 0_3_23 — Crosswalk region workspace and one-camera junction simulation

- Added an expanded in-page region workspace, separate from the compact Crosswalks layout, to create, rename, delete and drag four corner handles of quadrilateral regions against a selected camera/simulation frame.
- Saved per-crosswalk regions in the existing atomic JSON document, with backward compatibility for older saved crosswalks and validation for bounded, simple convex geometry. Both assigned cameras share one region set; there is no two-camera perspective calibration.
- Added shared camera simulation controls in Crosswalks and Junction Network using the existing global simulation API; exactly one simulated camera is previewed when enabled and physical streams follow existing pause/resume behavior.
- Added focused backend geometry/persistence regression and frontend wiring checks. No new model inference, pedestrian detection or signal-control authority.
- Passed baseline remains `0_3_11` pending owner acceptance.

## 0_3_22 — Missing FastAPI TestClient dependency on fresh Windows installs

- Added pinned `httpx==0.28.1` to backend requirements so `fastapi.testclient.TestClient` works in a newly created PC Studio virtual environment.
- The existing updater automatically reinstalls backend requirements after pulling this change. No other behavior, API, firmware or UI changes.
- Passed baseline stays `0_3_11` pending owner acceptance.

## 0_3_21 — Crosswalk schematic orientation correction

- Rotated zebra stripe geometry to seven horizontal white bars across the vertically oriented path connecting pedestrian Side A and Side B.
- Realigned the vertical path guides and corrected the accessible figure description; preserved two-camera assignments, controls and persistence.
- Extended the focused frontend structure regression. No backend, firmware, API or signal-control changes; accepted baseline stays `0_3_11`.

## 0_3_20 — Crosswalk definitions and two-sided camera assignment

- Added Traffic → Crosswalks page for create/edit/delete, schematic representation and two separate camera slots.
- Reused saved camera profiles for the two pedestrian approaches and displayed their current connectivity.
- Added isolated atomic crosswalk configuration storage, GET/PUT API, stable errors, and focused service/frontend regressions.
- No change to firmware, existing camera streaming, signal control or one-selected-source inference; passed baseline remains `0_3_11`.

## 0_3_19 — Camera Settings status and compact layout

- Removed verbose transport, version-specific and image-setting descriptions from Camera Settings.
- Added a color-coded, live-updating bar covering every saved ESP camera, with selected-preview identification and honest Streaming, Reconnecting, Paused, Connected, Unreachable, Error or Saved-only states.
- Kept selected-camera dropdown and stream Start/Stop visible; grouped IP/connection management, camera image/FPS controls and diagnostic telemetry into collapsible sections.
- Reused the existing camera status polling, transport/API and saved profile registry. No new backend endpoints, firmware or dependencies. `0_3_11` remains passed baseline pending owner PASS.

## 0_3_18 — Dedicated Camera Settings page

- Added Camera Settings to PC Studio navigation, distinct from Camera Sources simulation controls.
- Reused the existing saved ESP camera registry, per-camera IP/OV2640/FPS controls, MJPEG relay preview, and live device/stream diagnostics without new backend endpoints or firmware changes.
- Preview now clearly identifies the selected source and avoids showing simulation/stale frames as an ESP live feed; switching sources remounts the preview.
- Kept multiple ESP sessions but one selected camera input for shared inference/capture. Passed baseline remains 0_3_11 pending owner acceptance.

## 0_3_17 — Agent reading and editing workflow efficiency

Same-candidate integrity hardening:
- Reused shared atomic JSON persistence for dataset labels instead of a parallel writer.
- Prevented managed YOLO dataset rebuilds during active training with serialized startup/rebuild operations.
- Kept app-level bulk refreshes single-flight and prevented stale refreshes from overwriting changed camera mode.
- Handled initial Dataset Review and manual capture-list refresh failures visibly.
- Extended focused tests. No new features, security changes, firmware changes, or dependencies.


- Added an explicit owner-first, narrow-read workflow to `AGENTS.md` and `PATCH_PLAYBOOK.md`: confirm HEAD/version once, locate symbols/files before opening them, inspect only owning code/tests/contracts, and stop discovery when evidence is sufficient.
- Standardized minimum-scope edits, reuse of existing services, batched independent reads, related-test-first validation with risk-based escalation, and atomic GitHub commits with remote-head verification and no force pushes.
- Aligned `AI_AGENT_GUIDE.md`, `AI_AGENT_CHECKLIST.md`, and `DEVELOPMENT_WORKFLOW.md` without changing application architecture, APIs, frontend behavior, tests, firmware, or startup scripts.
- Preserved release-state, traffic safety, runtime-data, provenance and owner-acceptance gates. `0_3_11` remains the owner-confirmed passed baseline.

## 0_3_16 — Change-scoped startup checks

- Added optional -ChangedTests to the Windows update/test/run script; default remains full validation.
- Selected related offline regressions from changed Git files (latest commit when no update), and frontend typecheck/build for frontend changes.
- Added conservative full-suite fallback for shared/unknown/dependency changes.
- Kept runner/release checks, live health/smoke, dependency management, safe process replacement, and data preservation.
- Added deterministic selector and runner wiring regressions.
- Preserved all runtime APIs, traffic signal behavior, data formats and ESP transport; 0_3_11 remains passed baseline.

## 0_3_15 — Concurrency hardening and conflict cleanup

- Created V0315 / `0_3_15` after a deeper conflict/instability audit of unaccepted V0314; `passed_baseline` remains `0_3_11`.
- Upgraded `useSerialPolling` from timer-serial scheduling to one single-flight request owner shared by timer ticks, effect restarts, StrictMode replay and explicit refresh actions.
- Added `runNow()` and `waitForIdle()` controllers so manual refresh and state mutations can coordinate with active periodic reads instead of racing them.
- Removed the duplicate page-local Live AI detection timer and routed detection polling through the shared owner.
- Serialized dataset capture/delete, analytics clear, training start and camera simulation/physical-mode switching against conflicting status reads.
- Verified apparently redundant firmware compatibility files, fallback fixtures, Simulation Lab API and camera-diagnostic modules are active dependencies and retained them.
- Expanded structural/static regressions for the new single-flight and mutation-drain invariants.
- Preserved backend APIs, persistence schemas, signal safety/arbitration, network/simulation behavior, dataset/training/inference contracts, V0310 ATL1 production transport and the prototype-only public-road safety boundary.

## 0_3_14 — Frontend polling reliability and code optimization

- Created V0314 / `0_3_14` for the owner-requested whole-project code audit and optimization after unaccepted V0313; `passed_baseline` remains `0_3_11`.
- Audited release workflow, backend route ownership, major service hotspots, frontend periodic work and regression guards; avoided speculative reconstruction of tested backend signal/camera/data services where no concrete defect was found.
- Replaced the six remaining asynchronous `window.setInterval` polling loops in Camera Diagnostics, Dataset Capture, Live AI status, Logs, Traffic Analytics and Train / Export with the existing settled-task `useSerialPolling` helper.
- Added an explicit serial-polling restart key so Traffic Analytics still refreshes immediately when its query/filter scope changes without allowing overlapping requests.
- Fixed previously unhandled Live AI initialization and training/dataset status/settings promise failures by routing them into existing UI error state.
- Expanded structural/regression coverage so all known periodic surfaces share the serial helper and any future `window.setInterval` in frontend TypeScript/TSX fails validation.
- Preserved APIs, persistence schemas, request IDs, signal/safety behavior, network/simulation semantics, dataset/training/inference contracts, V0310 production camera transport, runtime data and the prototype-only public-road safety boundary.

## 0_3_13 — Code management and optimization

- Created V0313 / `0_3_13` at the owner's explicit request after unaccepted V0312; `passed_baseline` remains `0_3_11` until explicit acceptance.
- Modularized Junction Network frontend ownership: page state/mutations remain in `JunctionNetworkPage.tsx`, node-card presentation moved to `components/junctions/JunctionNodeCard.tsx`, and pure view/config helpers moved to `lib/junctionNetworkView.ts`.
- Replaced repeated junction/source scans in the frequently refreshed topology UI with memoized ID/source maps while preserving behavior and the V0312 non-clipping card layout.
- Optimized `JunctionNetworkOverviewService` so each saved ESP camera view is normalized once per overview and reused for junction assignment/summary work; focused regression verifies one projection per saved camera.
- Consolidated current-release/document/workflow structural validation into `scripts/check_structure.py`, removed the duplicate release-consistency regression, and simplified the Windows runner to one structure/release preflight plus runner self-regression.
- Updated durable code/playbook guidance to prevent duplicate validators and encourage clear page/presentation/helper ownership without state fragmentation.
- Preserved APIs, request IDs, persisted network schema, Junction Network semantics, single-selected-source live inference boundary, dataset/training/inference, signal simulation, V0310 `ATL1` production transport, runtime/user data, and prototype-only public-road safety boundary.

## 0_3_12 — Repository cleanup and runner hardening

- Created V0312 / `0_3_12` at the owner's explicit request after the owner-confirmed V0311 baseline; `passed_baseline` remains `0_3_11` until explicit acceptance.
- Removed obsolete root patch manifests/apply instructions, V010 test-ready instructions, duplicate legacy Windows launch/smoke wrappers, the historical V036 metadata finalizer and preservation-only regression, and the unused standalone V036 Arduino path while retaining current production/diagnostic paths.
- Replaced the stale release-specific root README with a durable project overview that points current release state to `VERSION`.
- Fixed a Windows runner regression observed during V0312 testing where the self-reloaded script could fail to bind array-splatted `-SkipUpdate` and recursively pull/reload. The reload now uses explicit switch binding and an `AITL_RUNNER_RELOADED` guard prevents unbounded recursion.
- Preserved V0311 Junction Network semantics, the single-selected-source live inference boundary, dataset/training/inference APIs, simulation/signal behavior, V0310 production `ATL1` transport, camera diagnostics, runtime/user data and the prototype-only public-road safety boundary.

## 0_3_11 — Junction Network visualization

- Created V0311 / `0_3_11` at the owner's explicit request after V0310; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Added a persistent Junction Network workspace that represents installed/model junctions as draggable nodes and existing directed topology links as lines.
- Extended schema-1 intersection metadata with deterministic/persisted canvas positions and an optional primary source while preserving backward loading of older schema-1 files.
- One junction may own multiple camera/source ids, while each source remains exclusive to one junction so live source-to-junction identity stays unambiguous.
- Added `GET /api/traffic/network/overview` to project topology, saved ESP camera health, selected/current source identity, current shared-pipeline vehicle/pedestrian load, phase/decision, ranked-scenario/service/test events and warnings.
- Added camera assignment/reassignment, primary-camera selection, junction add/remove/edit, link add/remove/enable/travel-time editing, load badges, event badges and warning indicators to the new frontend page.
- Preserved the existing single selected camera/simulation inference pipeline: only the resolved observation junction receives current AI/simulation traffic metrics; other junctions explicitly show unavailable occupancy rather than copied/fabricated data.
- Preserved V0310 camera transport, simulation/network-experiment semantics, API envelopes/request IDs, and the prototype-only no-public-road-control boundary.

## 0_3_10 — R10-tuned production camera pipeline

- Created V0310 / `0_3_10` at the owner's explicit request after V039; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Applied the strongest R10 physical tuning evidence to the actual ESP32-CAM production path while preserving the existing PC Studio session/API/wire contract.
- Kept one framebuffer and changed the PSRAM production grab policy from `CAMERA_GRAB_WHEN_EMPTY` to the R10-selected `CAMERA_GRAB_LATEST` freshness policy.
- Kept port 81 `aitl-tcp-jpeg-v1` / 16-byte `ATL1` framing but replaced the inherited real `sendmsg()` hot path with bounded plain non-blocking `send()` operations capped at the R10-winning 11,680-byte application write size.
- Preserved TCP_NODELAY/keepalive, progress/deadline limits, deterministic failed-frame socket close, no-catch-up scheduling, PC reconnect/session recovery, multi-camera selection and downstream CameraFrameService behavior.
- Preserved PC-owned frame size, JPEG quality and target FPS; V0310 does not force the diagnostic q18 result and does not restore automatic quality/resolution degradation.
- Did not add the Pi-style newest-frame cache because the strong-Wi-Fi R10 run showed no matched-target throughput benefit; the dedicated R10 diagnostic firmware remains available for A/B comparison.
- Added PlatformIO and Arduino IDE V0310 production entrypoints plus focused regression coverage. Physical acceptance still requires reflashing V0310 and measuring the real production ATL1 path; the diagnostic 12.43 FPS result is not relabeled as production evidence.

## 0_3_9 — Idempotent update / test / run workflow

- Created V039 / `0_3_9` as the next small candidate patch after V038; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Made `scripts/update_test_run.ps1` idempotent for normal Windows use: the same command now fast-forwards `main`, reloads the pulled helper, runs the established dependency/test/build/cleanliness sequence, safely replaces an already-running AiTL PC Studio instance, runs live smoke, and relaunches the frontend/backend.
- Existing listeners on ports 8000/5173 are terminated automatically only when Win32 executable/command-line evidence identifies them as this repository's AiTL PC Studio process tree; unrelated listeners are never killed automatically and still block startup with a clear safety error.
- Added regression coverage for AiTL-owned process-tree replacement, unrelated-port protection, retained fast-forward/tracked-work safeguards, and the prohibition on destructive `git clean` behavior.
- Preserved V038/R10 Camera Diagnostics, ESP production/diagnostic firmware, API envelopes, signal behavior, data/training/inference workflows, runtime data, and the prototype-only public-road safety boundary unchanged.
- Added V039 patch/current-candidate documentation and synchronized the shared frontend project-version source; `passed_baseline` remains `0_2_4` until explicit owner acceptance.

## 0_3_8 — One-click camera diagnostics

- Created V038 / `0_3_8` at the owner's explicit request after V037; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Added a separate **Camera Diagnostics / Camera Test** page under Operate with one **Diagnose camera** action for the currently selected saved ESP.
- Added `POST /api/camera/diagnostics/run` and a dedicated `CameraDiagnosticService`; the route remains thin and the service owns staged measurement, classification, and state restoration.
- One diagnostic run measures repeated ESP `/status` control reachability/latency, protocol and camera readiness, RSSI/BSSID/channel, direct `ATL1`/JPEG receiving, direct receiving with concurrent status polling, and the normal `RemoteCameraManager` / `RemoteCameraService` stream path.
- Added evidence-based diagnoses for control-unreachable, incompatible firmware, camera-not-ready, ESP camera/TCP send stall, direct-stream failure, HTTP-control/stream contention, PC Studio stream integration, intermittent control-plane response, weak Wi-Fi margin, and healthy-now.
- Diagnostics temporarily use the selected camera's saved image settings at 5 FPS, then restore the original saved FPS/settings plus prior connected/streaming/simulation state; runtime camera-profile data is not replaced by the patch.
- Existing V037/R6 ESP firmware, `aitl-camera-v037` identity, and `aitl-tcp-jpeg-v1` wire format remain unchanged, so V038 does not require an ESP reflash.
- No UDP transport, ESP-side inference, persistent diagnostic history, new stable error code, or physical/public-road signal authority is introduced.

- V038 R2 expands Camera Test from a short layer check into a detailed functionality, stability, and bottleneck diagnostic while staying on candidate `0_3_8`.
- R2 adds repeated control latency distribution, camera config/start/stop lifecycle verification, direct JPEG integrity and frame-timing statistics, control-vs-stream contention measurement, saved-target throughput/headroom testing up to 15 FPS, intentional reconnect verification, and normal managed-worker measurement.
- R2 reports a 0–100 stability score and explicit bottleneck attribution for control latency, RF margin, throughput capacity, frame jitter, control/data contention, ESP/TCP sender, and PC Studio receive integration.
- R2 changes managed-worker evidence to per-phase counter deltas and separates diagnostic-induced socket-reset send failures from unexpected in-phase ESP failures, avoiding misleading cumulative/transition failure counts.
## 0_3_7 — Quality-preserving ESP streaming

- Created V037 / `0_3_7` at the owner's explicit request after V036; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Preserved the V036 multi-ESP architecture, PC-controlled session lifecycle, 16-byte `ATL1` framing and `aitl-tcp-jpeg-v1` wire format.
- Added adaptive ESP-side JPEG compression with QVGA / JPEG 24 / 15 FPS defaults for new profiles while preserving existing saved profiles.
- R2 targets roughly 5000-byte JPEG payloads, below the classic ESP32 lwIP default TCP send-buffer boundary observed in physical V036 testing.
- R2 skips oversized captures locally while compression can still increase, avoiding partial length-prefixed frames and avoidable reconnects during adaptation.
- R2 learns a lower conservative payload target from real partial-send accepted-byte evidence and uses proportional compression steps for large oversize gaps.
- R2 increases the bounded adaptive compression ceiling to JPEG quality number 50 and slows recovery until strong payload headroom is sustained.
- PC Studio requests a 256 KiB receive buffer and Camera Sources exposes effective/configured quality, send EWMA, payload target, local oversize-drop count and window-learn count.
- PC Studio remains migration-compatible with `aitl-camera-v036` nodes using the same TCP frame protocol, but V037 adaptive behavior requires V037 firmware.
- R3 permanently removes the historical V036 metadata-finalizer hook from the normal update/test/run helper, so validation no longer rewrites tracked `CHANGELOG.md` or frontend version metadata and the next normal Git pull is not blocked by runner-created edits. A post-test cleanliness guard now catches any future helper that dirties tracked source.
- R4 fixes an R2 physical-test bug where frames larger than the adaptive payload target were sent anyway after JPEG compression reached its ceiling. V037 now drops that capture and temporarily steps only the effective sensor resolution down until the frame fits; sustained low-send-time headroom restores resolution one step at a time before JPEG quality is recovered. Saved resolution remains unchanged.
- R4 adds configured/effective frame-size, resolution downshift/recovery, and actual frame-dimension telemetry so physical adaptation is visible in Serial Monitor and Camera Sources.
- R6 follows controlled camera-only and TCP-only isolation tests. One-buffer `CAMERA_GRAB_WHEN_EMPTY` camera capture at 20 MHz was stable, and synthetic 8/16/32 KiB ATL1 records completed 1040 TCP sends with zero send failures on the healthy BSSID, disproving the R2/R4 assumption that a JPEG must fit a ~5.7 KiB lwIP send buffer.
- R6 removes the 3.8–5 KB payload target, partial-send target learning, local oversize rejection, automatic q=50 compression escalation and effective-resolution downshift. Configured JPEG quality/resolution now remain fixed across transport pressure.
- R6 uses one UXGA-capable PSRAM framebuffer with `CAMERA_GRAB_WHEN_EMPTY`, keeps 20 MHz XCLK, flushes the pending idle frame at new TCP-client connection, and retains freshness-first scheduling with no catch-up backlog.
- R6 relaxes steady-state send guardrails to 700 ms no-progress / 1500 ms total (1200 / 2000 ms during connection warmup), while retaining non-blocking vectored `sendmsg`, `TCP_NODELAY`, keepalive, deterministic partial-frame socket close, and the existing PC reconnect/session-recovery worker.
- R6 adds RSSI/BSSID/channel and ESP Wi-Fi disconnect/reconnect telemetry. Legacy R2/R4 adaptive keys remain zero-valued for same-candidate API compatibility, and Camera Sources now presents the quality-preserving policy plus Wi-Fi diagnostics instead of the obsolete payload-target controls.
- R7 fixes intermittent PC Studio **Connect** 502 failures observed while the R6 ESP remained Wi-Fi-associated: all low-rate HTTP control operations are now serialized per camera session, preventing frontend `/remote/status` polling from racing button/reconnect traffic against the ESP's single-threaded WebServer.
- R7 retries only transport-level ESP control failures up to three times using fresh HTTP connections and short bounded backoff. Real HTTP responses, validation failures and protocol incompatibilities still fail immediately instead of being hidden by retries. The persistent TCP JPEG data plane and R6 firmware are unchanged.
- No ESP-side inference, UDP transport, physical/public-road signal authority or rewrite of runtime camera-profile data is introduced.
## 0_3_6 — Low-latency binary TCP multi-ESP camera input

- Created V036 / `0_3_6` after V035 to improve physical ESP32-CAM streaming speed and reduce end-to-end latency; V024 / `0_2_4` remained the owner-confirmed passed baseline.
- Replaced the ESP-to-PC HTTP/MJPEG hot path with persistent length-prefixed binary TCP JPEG on port 81 while retaining HTTP port 80 for status/config/start/stop/diagnostics.
- Added `aitl-tcp-jpeg-v1`: ATL1 magic, JPEG length, source sequence, ESP uptime and JPEG payload.
- Preserved Connect as zero-image status/control only and Start as `/stop` best effort -> full `/config` -> `/start` -> TCP open.
- Added freshness-first socket deadlines, TCP_NODELAY/keepalive, PSRAM double buffering, `CAMERA_GRAB_LATEST`, reconnect/recovery behavior and PC exact-length frame validation.
- Added saved multi-ESP profiles and simultaneous independent stream workers/caches; exactly one selected ESP feeds the shared downstream `CameraFrameService`.
- Hardened switching against stale caches, in-flight source races and retired-session late frames; added numeric resolution display and retained simulation compatibility.
- Same-candidate physical repairs progressed through non-blocking send, progress-bounded send and R6 connection-warmup vectored send after hardware logs exposed TCP buffer/backpressure behavior.
- No ESP-side inference, public-road control, or new stable error code was introduced.
## 0_3_5 — Resilient low-latency ESP streaming

- Created V035 / `0_3_5` at the owner's explicit request after V034 to further improve physical-camera speed, connection stability and the streaming workflow; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Kept the V033/V034 safety/traffic contract: Connect remains status/control only with zero image transfer; Start applies complete PC-owned settings before `/start`; Stop closes image transport before `/stop`.
- Replaced the V034 `urllib` stream opener with a direct `http.client.HTTPConnection` transport so the PC can enable TCP keepalive/TCP_NODELAY and use a dedicated stream read timeout.
- Replaced JPEG SOI/EOI scanning with a multipart `Content-Length` parser that handles arbitrary TCP chunk boundaries and extracts exact JPEG parts.
- Increased stream read size from 4 KiB to 64 KiB to reduce Python/network-read overhead while still retaining newest-frame backlog dropping.
- Added event-driven physical-frame wakeups for `/api/camera/live.mjpeg`, removing V034's 10 ms browser-preview polling loop for ESP frames.
- Added automatic ESP session recovery: after a dropped connection or ESP reboot, the backend probes `/status`, reapplies the retained settings and target FPS if the session was lost, calls `/start`, then reopens MJPEG.
- Added bounded exponential reconnect backoff plus `stream_connected`, session-recovery, failure-streak and backoff telemetry.
- Matching ESP firmware adds TCP_NODELAY, HTTPD TCP keepalive, shorter send/receive timeouts, two writes per MJPEG frame instead of three, stream-client status, and less disruptive Wi-Fi reconnect handling.
- Simulation still suspends physical image transfer and automatically resumes it afterward.
- No ESP-side inference, public-road control, or independent simultaneous multi-camera frame store is introduced.
## 0_3_4 — Low-latency persistent ESP MJPEG transport

- Created V034 / `0_3_4` at the owner's explicit request after V033 to improve physical-camera streaming speed and reduce latency; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Preserved V033's idle/connect/config/start/stop contract: Connect still performs status/control only and transfers zero image bytes.
- Replaced repeated one-request-per-frame `/capture` polling with one persistent ESP `:81/stream` MJPEG connection after Start Stream.
- Added PC-selected `target_fps` (1–30), sent to the ESP with the complete OV2640 configuration as `stream_fps`; V033 `fetch_interval_ms` callers remain accepted as a compatibility alias.
- Added incremental JPEG SOI/EOI extraction from the persistent MJPEG byte stream, immediate newest-frame ingestion into the existing `CameraFrameService`, stream reconnect handling, transport byte/reconnect counters, measured FPS and frame-interval telemetry.
- Added `GET /api/camera/live.mjpeg` so Camera Sources receives a backend MJPEG preview from the same current-frame pipeline instead of waiting for React camera-status polling to refresh still-image URLs.
- Updated matching ESP firmware to retain `CAMERA_GRAB_LATEST`, two PSRAM framebuffers, Wi-Fi sleep disabled, and a PC-controlled target-FPS cap to prevent stale-frame buffering.
- Starting Camera Sources simulation pauses/closes the active ESP image stream; stopping simulation reopens it without reconfiguring the session.
- Updated inherited V033 remote-camera regressions to validate persistent MJPEG transport and compatibility behavior.
- No ESP-side inference, multi-camera independent buffer store, physical signal output, or public-road control path is introduced.
## 0_3_3 — PC-controlled on-demand ESP camera session

- Created V033 / `0_3_3` at the owner's explicit request after V032; V032 remains the previous candidate and V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Changed the remote ESP workflow so **Connect** probes only the ESP `/status` control surface and does not request or transfer an image.
- Added explicit **Start Stream** / **Stop Stream** lifecycle. Start sends the complete validated OV2640 runtime settings to the ESP `/config`, activates `/start`, and only then starts bounded PC-side `/capture` polling. Stop ends PC polling and calls ESP `/stop`, returning the camera session to idle while keeping the device connected.
- Added PC-controlled resolution, JPEG quality, brightness, contrast, saturation, effect, white-balance, exposure, gain, correction, mirror/flip/downsize and color-bar settings plus PC capture interval.
- Added `POST /api/camera/remote/start` and `POST /api/camera/remote/stop`; V032 connect/disconnect/status and legacy raw frame upload remain compatible.
- Added matching Arduino IDE V033 firmware whose `/capture` and `:81/stream` endpoints refuse image transfer unless a PC-started session is active.
- Built-in simulation pauses PC frame requests without discarding the configured ESP session, and frame requests resume afterward.
- No physical/public-road signal command path is introduced.
## 0_3_2 — PC-pull ESP32-CAM integration

- Created V032 / `0_3_2` at the owner's explicit request while V031 remained unaccepted; V024 / `0_2_4` remains the owner-confirmed passed baseline.
- Added private-LAN PC-pull integration for the stock Arduino ESP32 CameraWebServer: PC Studio probes `/capture`, continuously ingests JPEG snapshots into the existing CameraFrameService path, and exposes the `:81/stream` preview URL.
- Added `GET /api/camera/remote/status`, `POST /api/camera/remote/connect`, and `POST /api/camera/remote/disconnect` with standard envelopes/request IDs.
- Restricted remote camera targets to literal RFC1918 IPv4 ranges; no general arbitrary URL fetcher or public-IP camera fetch is introduced.
- Added Camera Sources ESP IP/source controls, connect/reconnect/disconnect state, remote health telemetry, direct MJPEG preview with backend-frame fallback, and simulation coexistence.
- Starting simulation pauses remote ESP ingestion and stopping simulation resumes it; the existing raw JPEG/PNG POST receiver remains backward compatible.
- Added focused remote-camera regression coverage. No ESP-side inference, physical signal output, or public-road traffic-control authority is introduced.
## 0_3_1 — Persistent normalized decision evidence

- Created V031 / `0_3_1` at the owner's explicit request while keeping V024 / `0_2_4` as the owner-confirmed passed baseline and V030 as the previous unaccepted candidate.
- Preserved all seven V030 network comparison modes and existing protected timing behavior; V031 is an additive evidence/traceability layer rather than a new control mode.
- Added schema-versioned (`schema_version: 1`) normalized decision evidence covering ranked scenarios, neighbour cooperation, pedestrian-awareness guards, vehicle-class priority, emergency priority, and emergency lifecycle records.
- Added deterministic evidence IDs and normalized fields for mode/time/intersection/link/trigger category, grant/deny/defer/observe decision, action, applied flag, before/after timing, reason, concise explanation, relevant local/neighbour/pedestrian/class/emergency context, provenance, and a source reference back to the detailed mode-specific history.
- Added scenario evidence snapshots in the isolated network simulator so V031+ runs retain the local observations and ranked-winner context used by the simulated controller; historical V030 runs can still project all evidence available in their already-stored raw histories.
- Preserved detailed mode-specific histories for backward compatibility and added a compact `decision_evidence` projection plus list-summary record/applied counts.
- Added `GET /api/traffic/network-experiments/{run_id}/evidence` and `GET /api/traffic/network-experiments/{run_id}/evidence.csv`; CSV preserves `X-Request-ID`. Older stored runs without the V031 block are projected on demand without being rewritten.
- Kept evidence records repeatable by excluding volatile random run IDs from record content while retaining deterministic source references/IDs.
- Added focused V031 evidence regression and retained V027/V028/V029/V030 focused regressions. No new stable error code or physical/public-road control path was introduced.
- Same-candidate V031 repair: a pedestrian request at/above the configured maximum wait now creates a cross-layer starvation-prevention lock that defers ordinary network cooperation and regular vehicle-class priority until pedestrian WALK/CLEAR begins; the simulated emergency layer remains separate, and active crossing protection still governs emergency timing.
- Same-candidate V031 repair: cooperation, pedestrian-awareness, vehicle-class, and emergency-priority detailed events now retain `previous_duration_seconds` and `effective_duration_seconds` in addition to timing delta, and the normalized ledger projects those values when available.
- Same-candidate V031 repair: non-applied pedestrian `pedestrian_service_pending` / `pedestrian_request_queued` evidence is normalized as `defer` rather than `observe`; focused regression now covers cross-layer suppression and timing reconstruction.
- Same-candidate V031 conflict repair: added a pure `network_policy_arbiter.py` that selects exactly one higher-level network timing overlay owner per intersection/tick using the explicit order incident hold > active pedestrian crossing > simulated emergency priority > pedestrian max-wait > configured class priority > network cooperation. Ranked scenarios remain the controller-owned base policy.
- Same-candidate V031 conflict repair: post-advisory re-reads now use non-reapplying benchmark snapshots instead of re-running ranked-scenario evaluation, preventing call-order-dependent scenario reapplication between policy layers.
- Same-candidate V031 conflict repair: benchmark protected-service requests now retain service/source/priority/start metadata, suppress lower-priority replacement, record start/suppression/satisfaction lifecycle events, and clear when the requested protected service begins.
- Added arbitration context/metrics/transition events and normalized evidence `context.arbitration`; documented that the seven network modes remain comparison/ablation modes rather than one all-features-integrated controller.
- Corrected stale V027 headings/version expectations in V031 local-testing and acceptance guidance and strengthened the handoff workflow toward atomic commits/PRs plus an immutable accepted tag after explicit owner acceptance.
- Same-candidate V031 explanation hardening: live `decision_context.requested_service` now requires explicit active service-request lifecycle evidence instead of treating the legacy stale-capable `pending_request` flag as causal state; added a focused regression for this distinction.
## 0_3_0 — Vehicle-class-aware cooperative two-intersection simulation

- Created V030 / `0_3_0` at the owner's explicit request while keeping V024 / `0_2_4` as the owner-confirmed passed baseline and V029 as the previous unaccepted candidate.
- Added explicit regular synthetic class taxonomy `car`, `bus`, `truck`, `motorcycle`, `bicycle`, `other`, with unknown/unmapped regular labels normalized to `other`; retained V029 `emergency` as a separate special simulator class.
- Added deterministic `legacy`, `mixed_urban`, and `freight_heavy` class profiles; all seven network modes in one run receive the same seeded class-rich base arrival plan.
- Added `class_aware_cooperative` as a seventh mode, preserving Pedestrian-aware Cooperative behavior while optionally applying one configured regular-class weight/priority layer.
- Added bounded class-aware vehicle service: neutral weight `1.0` causes no timing change; configured weight above `1.0` may extend vehicle green within class/phase/cycle caps or request earlier protected vehicle service by reducing only the current phase toward its minimum. Active pedestrian WALK/CLEAR demand blocks class-priority shortening.
- Added per-intersection and network per-class external/transfer arrivals, served counts, wait distributions, and queue average/p95/peak plus class counts in the deterministic arrival-plan snapshot.
- Added structured class-priority events/telemetry with intersection/role/class/wait/weight/action/timing/reason fields and explicit `synthetic_vehicle_class_demand` provenance.
- Added `comparisons.class_aware_cooperative_vs_pedestrian_aware_cooperative` with selected-class served/wait/queue deltas, plus seven-mode CSV class-priority columns.
- Added request fields for class profile, enable flag, selected class, weight, minimum waiting count, and maximum extension; no new stable error code was required.
- Added focused V030 class-aware regression including direct protected-bound, pedestrian-protection, neutral-weight, deterministic-profile, disabled-layer-equivalence, persistence and CSV checks while retaining V027/V028/V029 regressions.
- Synthetic class generation is simulator evidence only; no live class-accuracy, public-transit priority, hardware/public-road control, or safety claim is introduced.
## 0_2_9 — Simulated emergency-priority cooperative two-intersection simulation

- Created V029 / `0_2_9` at the owner's explicit request while keeping V024 / `0_2_4` as the owner-confirmed passed baseline and V028 as the previous unaccepted candidate.
- Preserved the four V028 network modes and added matched `emergency_baseline_cooperative` and `emergency_priority_cooperative` modes so emergency-priority effects are compared against the same seeded base demand and the same simulated emergency event.
- Added a deterministic/configured emergency event with event/vehicle/type/source/destination/link identity, explicit simulation provenance, no detector-confidence claim, and lifecycle evidence for activation, source departure, downstream arrival, clear, and recovery.
- Added bounded emergency priority that may extend current vehicle green within phase/cycle caps or request earlier protected progression only toward the current phase minimum. Active simulated pedestrian crossings deny the emergency timing change until clearance.
- Added source priority, downstream preparation, destination priority, grant/deny/defer explanations, timing deltas, emergency wait/travel telemetry, lifecycle/priority event histories, and matched Emergency-priority-vs-Emergency-baseline comparison.
- Extended network CSV with emergency status/role/decision/action/ETA/applied fields for all six modes.
- Added request fields for emergency enable/time/type, downstream lookahead, and maximum green extension; no new stable error code was required.
- Added focused V029 regression including direct protected-bound/emergency-crossing-guard tests while retaining V027 cooperation and V028 pedestrian-aware regressions.
- Live emergency recognition, hardware/public-road pre-emption, cabinet integration, and safety-certification claims remain out of scope.
## 0_2_8 — Pedestrian-aware cooperative two-intersection simulation

- Created V028 / `0_2_8` at the owner's explicit request while keeping V024 / `0_2_4` as the owner-confirmed passed baseline and V027 as the previous unaccepted candidate.
- Corrected a GitHub-main inconsistency discovered during V028 preflight: V027 models/tests/docs described cooperative mode while `network_simulation_experiments.py` was still the V026 independent implementation. V028 carries the complete intended V027 cooperative service forward before adding V028 behavior.
- Added a fourth `pedestrian_aware_cooperative` network mode so Fixed, Independent Adaptive, Cooperative Adaptive, and Pedestrian-aware Cooperative share one seeded exogenous demand plan.
- Added pedestrian request lifecycle and evidence: request start/fulfillment counts, service sessions, request-fulfillment distribution, maximum observed wait, crossing occupancy and crossing peak.
- Added bounded starvation prevention: once oldest waiting time reaches the configured threshold, the simulator requests pedestrian service and may shorten only the current protected phase toward its configured minimum.
- Added synthetic crossing-clearance protection: served pedestrians remain in simulated crossing occupancy for a configured clearance interval; active WALK/CLEAR may be extended within saved phase/cycle maxima to preserve a configured clearance reserve.
- Strengthened V027 cooperation so waiting **or crossing** pedestrian demand prevents neighbour coordination from shortening pedestrian WALK/CLEAR.
- Added pedestrian-awareness events/provenance, network metrics, pairwise Pedestrian-aware-vs-Cooperative comparisons, and aligned four-mode CSV fields.
- Added request bounds for max pedestrian wait, synthetic crossing clearance time, and clearance reserve. Emergency priority and live cross-camera pedestrian identity remain inactive.
## 0_2_7 — Bounded cooperative two-intersection network simulation

- Created V027 / `0_2_7` at the owner's explicit request while keeping V024 / `0_2_4` as the owner-confirmed passed baseline; V026 remains the previous unaccepted candidate.
- Extended the V026 deterministic two-intersection network experiment from Fixed/Adaptive to Fixed / Independent Adaptive / Cooperative Adaptive using the same seeded exogenous demand and topology/policy snapshots.
- Added simulation-only predicted-arrival cooperation: downstream B consumes synthetic A→B transfers already in the configured-link pipeline and evaluates incoming count/earliest ETA inside a bounded lookahead.
- Added protected cooperative timing advisories: bounded vehicle-green extension within saved phase/cycle caps, or earlier protected progression by reducing only the current phase toward its configured minimum. Active local pedestrian demand prevents cooperation from shortening pedestrian WALK/CLEAR.
- Added structured coordination events and network coordination telemetry for evaluations, triggers, applied advisories, green extensions, progression requests, pedestrian-service protections, and timing seconds added/reduced.
- Preserved backward-compatible Adaptive-vs-Fixed `comparison` and added pairwise `comparisons` for Cooperative-vs-Fixed and Cooperative-vs-Independent-Adaptive.
- Expanded network CSV export to aligned Fixed / Adaptive / Cooperative source/destination/network fields plus cooperation action/incoming/ETA/applied columns.
- Added bounded request fields for cooperation lookahead, max extension, and minimum incoming vehicles; reused existing traffic-rule/network validation error paths.
- Kept network experiments isolated from the live camera/controller runtime. Emergency priority, live cross-camera transfer/identity, measured travel-time prediction, general N-intersection cooperative orchestration, and physical/public-road traffic control remain outside V027.
## 0_2_6 — Deterministic two-intersection network simulation

- Created V026 / `0_2_6` after V025 while V025 remained unaccepted; `previous_version` is `0_2_5` and the owner-confirmed `passed_baseline` remains V024 / `0_2_4`.
- Added an isolated deterministic two-intersection network experiment service that selects one enabled directed topology link and models its configured upstream/downstream intersections simultaneously.
- Each simulated intersection owns a separate signal-controller runtime using the existing ranked-scenario/phase implementation; V026 does not relabel one global controller as two intersections.
- Fixed and Adaptive network runs receive the same seeded exogenous vehicle/pedestrian arrival plan; the stored scenario includes demand counts and a SHA-256 plan fingerprint for auditability. Upstream policy outcomes may change when transfer candidates are discharged, which intentionally changes downstream transfer-arrival timing as an experiment outcome.
- Added synthetic A→B vehicle transfer over the configured link travel time, including bounded per-vehicle departure/scheduled-arrival/arrival evidence and transfer-pipeline occupancy telemetry.
- Added per-intersection wait/queue/throughput/signal/scenario metrics plus network corridor completions, end-to-end corridor travel-time distribution, total vehicle wait/queue pressure, and Fixed-vs-Adaptive network comparisons.
- Added persistent `netexp_*.json` results and aligned timeline CSV export under the existing ignored `outputs/simulation_experiments/` runtime area.
- Added `POST/GET /api/traffic/network-experiments`, `GET /api/traffic/network-experiments/{run_id}`, `GET /api/traffic/network-experiments/{run_id}/export.csv`, and `DELETE /api/traffic/network-experiments/{run_id}` with existing request-ID/envelope conventions and experiment/network error paths.
- Added focused deterministic regression coverage for arrival-plan repeatability, two independent intersection states, exact configured link travel time, transfer evidence, persistence/list/get/delete/CSV, and missing-link rejection.
- The existing PC Studio Simulation Lab UI remains the single-junction Fixed-vs-Adaptive surface in V026; the network experiment is API/test-first so the next cooperation patch can compare against a stable independent-control baseline.
- Cooperative neighbour-informed timing, emergency priority, real emergency perception, and physical/public-road traffic control remain disabled.
## 0_2_5 — Ranked signal scenarios and simulation telemetry

- Same-candidate documentation hardening: added `docs/DOCUMENTATION_MAP.md` and `docs/PROJECT_SCOPE.md`, removed stale current-version/placeholder ownership from durable human/agent/workflow/versioning/debugging/UI guides and PC Studio app READMEs, refreshed data semantics, and clarified documentation authority/maintenance rules.
- Documented the planned invention capability sequence and evidence boundaries for multi-intersection cooperation, emergency priority, pedestrian-aware control, different vehicle classes, and explainable decisions; configured network links remain foundation metadata rather than active cooperation.
- Owner explicitly accepted/promoted V024 / `0_2_4`; V025 now records `passed_baseline: 0_2_4` while remaining the current unaccepted candidate.
- Same-candidate network-foundation update: added persistent generic intersection/topology metadata, source-to-intersection resolution, directed neighbour links, and runtime `config/intersections.json` without promoting V025 or enabling cooperative control.
- Added `GET/PUT /api/traffic/network`, `POST /api/traffic/network/reset`, and `GET /api/traffic/network/context` with standard envelopes/request IDs, atomic persistence, validation, and stable `ATL-TRAFFIC-013..015` errors.
- Enriched `GET /api/traffic/state` with `intersection_id`, explicit observation provenance, configured neighbour context, and structured live `decision_context` including deterministic decision id, trigger category, winning scenario/observed conditions, requested service, timing, pedestrian/vehicle context, emergency-placeholder state, neighbour context, and a readable explanation.
- Kept the current live camera/tracker/controller runtime single-junction: topology links do not coordinate timings, transfer simulated agents, predict arrivals, or implement emergency priority; the API explicitly reports those capabilities inactive.
- Reworked Traffic Logic adaptive rules into editable ranked **scenarios**. Each scenario has an id/name, enable flag, rank (`1` highest), ALL/ANY condition matching, persistence/cooldown, bounded phase targets/action, and optional pedestrian/vehicle service request.
- Added first-class zone/class conditions so a scenario can express cases such as `car > 5 in queue_a` or `person >= 3 in waiting_west`, including `*` for all detected classes in a configured polygon zone.
- Extended traffic-state observations with `zone_class_counts`, preserving arbitrary detected class names for scenario evaluation while keeping occupancy and track-derived flow semantics separate.
- Changed adaptive arbitration so multiple scenarios may trigger but only the highest-ranked **eligible** scenario executes per evaluation; disabled/stale/unavailable/current-phase-ineligible/cooldown scenarios are explained and do not block the next eligible scenario.
- Migrates inherited V023 rule definitions into editable scenario definitions when an older saved config has no `scenarios` field, preserving default behavior and existing profile/timing data.
- Kept protected phase order/minimums/max/cycle bounds and Test-mode incident/accessibility semantics; `request_next_phase` only requests earlier protected progression rather than directly jumping conflicting movement phases.
- Rebuilt Traffic Logic as compact Live Decision / Signal Timing / Scenario Rules / Test & Safety / History tabs with zone/class selectors, rank controls, condition builders, action/phase selectors, winner explanations, and live observed values.
- Added an isolated deterministic Simulation Lab that runs the selected saved signal profile in Fixed and Adaptive modes from the same requested density and seed without resetting the live Camera Sources simulation or live controller runtime.
- Added richer experiment telemetry: vehicle/pedestrian wait count/average/median/p95/max/total, queue average/p95/peak/queue-seconds/active share, simultaneous queue time, vehicle/pedestrian/combined throughput, vehicle-green efficiency, phase utilization, clearance time/share, transitions/cycles, adaptive scenario applications, timing extensions/reductions, and a simulator conflict-overlap diagnostic.
- Added bounded persistent experiment results under `outputs/simulation_experiments/`, stored-run list/get/delete operations, and aligned Fixed/Adaptive timeline CSV export with `X-Request-ID`.
- Added `POST/GET /api/traffic/experiments`, `GET /api/traffic/experiments/{run_id}`, `GET /api/traffic/experiments/{run_id}/export.csv`, and `DELETE /api/traffic/experiments/{run_id}` with standard envelopes/request IDs.
- Added stable experiment storage errors `ATL-TRAFFIC-010..012`.
- Added a compact one-page Simulation Lab presentation with top-level run controls, stored-run dropdown, Summary / Waiting & queues / Throughput / Signal behavior / Raw samples tabs, Fixed/Adaptive sample toggles, page-size selection, and pagination/internal scrolling so telemetry does not become one long dashboard.
- Added focused ranked-scenario and deterministic experiment regression coverage. Simulation Lab now snapshots configured zones and supplies synthetic per-zone/per-class observations so zone-based scenarios can be exercised in isolated Adaptive runs. Existing V024 persistence/polling hardening, V022 tracking/flow, V021 occupancy, dataset/training/inference/model workflows, and prototype-only safety boundaries remain preserved.
- Physical/public-road traffic control remains disabled; experiment results are local synthetic benchmark data only.
## 0_2_4 — Maintenance hardening and polling optimization

- Refined the signal-aware simulator presentation by shrinking the top-left metadata banner and the right-side pedestrian signal display so more of the synthetic roadway remains visible in Live AI and Camera views.
- Same-candidate Windows runner repair: replace an invalid Python-style `elif` with PowerShell `elseif` after the frontend/build checks, and extend the runner regression to reject that syntax error before handoff.

- Same-candidate Windows atomic-write repair: serialize the final `os.replace` step and retry bounded transient `PermissionError` sharing violations; keep 32-writer concurrency coverage and add a deterministic retry-path regression.
- Refined PC Studio presentation using Material role-based color semantics: neutral surfaces dominate, primary blue identifies navigation/main actions, secondary teal is sparse for selection/progress, and generic badges are neutral instead of implicitly green.
- Reworked visible UI copy across Dashboard, Camera Sources, Live AI, Zones, Analytics, Dataset, Training, Models, Settings, Logs, navigation, and capability panels to describe current tasks/states rather than old version history or placeholder language.
- Added explicit primary/secondary/on-color roles, semantic action/button hierarchy, clearer destructive treatment, and copy/style guardrails while preserving the Material `#121212` dark surface ramp and system light/dark adaptation.
- Added and hardened `scripts/update_test_run.ps1`: it protects tracked local work, requires `main` for automatic update, fast-forwards from `origin/main`, reloads the pulled runner, synchronizes dependencies, runs backend/frontend validation plus live smoke after health readiness, and launches PC Studio on strict known ports without deleting runtime data.

- Created V024 / `0_2_4` at the owner's explicit request while keeping owner-confirmed `passed_baseline: 0_2_2`; V023 was not implicitly promoted.
- Added shared `app/core/json_store.py` atomic JSON persistence using a unique same-directory temporary file, flush/fsync, and `os.replace`, with cleanup on failure.
- Migrated runtime settings, editable zones, and model-registry metadata to the shared JSON persistence helper without changing their API envelopes or stable error codes.
- Serialized zone configuration writes with the existing service lock and added a re-entrant model-registry lock so discovery/default/delete/metadata transitions do not race inside the process.
- Added reusable frontend `useSerialPolling` scheduling so the top-level camera-status and Live AI traffic/zone refresh loops wait for each async poll to settle before scheduling the next one.
- Added focused atomic-persistence regression coverage and repository architecture guards against fixed shared `.tmp` files, direct JSON writes in migrated services, or reintroduced top-level `setInterval` polling.
- Preserved V023 adaptive signal behavior and Material-derived PC Studio design system, V022 tracking/flow, V021 occupancy, dataset/training/inference/model workflows, request IDs, logging, and prototype-only safety boundaries.
- No API endpoints, schemas, or stable error-code definitions changed. Physical/public-road traffic control remains disabled.
## 0_2_3 — Configurable adaptive signal rules

- Same-candidate Material dark-theme refinement: use the Material 2 `#121212` base, explicit 0/1/2/4/8dp surface-lightness ramp, low-opacity on-surface borders, Blue Grey light/desaturated interaction tones, and sparse light semantic accents so dark mode communicates elevation and hierarchy without neon/AI-dashboard coloring.
- Same-candidate visual refinement: align the new PC Studio design system with Apple HIG, Material color-role guidance, and the supplied Figma/UX Pilot color-theory references; add automatic system light/dark appearance, base/elevated neutral layers, a single restrained interaction family, contrast/accessibility media preferences, and clearer hierarchy without changing application behavior.
- Same-candidate visual-system patch: centralized PC Studio styling under token/base/layout/component CSS, documented the design system, and replaced the gradient/glass/neon-purple dashboard treatment with a restrained graphite operations/workbench theme using smaller radii and semantic color roles.
- Same-candidate inherited-test repair: align `test_zone_traffic_services.py` with V023's intentional `Detection recommendation:` explanation text while preserving the existing `recommended_phase`, `recommended_decision`, and recommendation-reason assertions.
- Same-candidate test-harness repair: add the PC Studio backend directory to `scripts/test_signal_rules_service.py` import path so the standalone regression script can resolve `app` from the project root.
- Same-candidate repair: handle intentional backward simulation-clock seeks by rebuilding transient signal-controller phase state, preserving inherited deterministic camera simulation tests.

- Promoted the owner-confirmed passed baseline to V022 / `0_2_2` and created V023 / `0_2_3` as the new candidate.
- Replaced the simulator's hard-coded signal-duration sequence with a persistent user-configurable simulation policy while preserving the protected phase order.
- Added editable min/base/max timing for vehicle green, vehicle yellow, both all-red clearances, pedestrian WALK, and pedestrian CLEAR plus a maximum-cycle bound.
- Added Fixed, Adaptive, and Test modes, dry-run evaluation, and Normal / Pedestrian Priority / Vehicle Priority / Accessibility profiles.
- Added bounded structured rules for crossing occupancy/slow crossing, pedestrian queue/max wait, low vehicle demand, vehicle queue/max wait, mobility assistance, and fallen-person incident test input.
- Added priority arbitration, persistence/hysteresis, cooldown/retrigger protection, short-term demand memory, stale-data fallback, pending demand, minimum-service clamps, and bounded phase/cycle timing.
- Added explicit Test-mode accessibility/incident inputs without claiming unsupported live wheelchair/fall detection.
- Added simulated all-red incident hold, explicit clear/recovery, and transient adaptive-state reset separate from saved configuration.
- Added non-mutating rule previews and persistent runtime signal-decision history under `outputs/signal_rules/` with explicit history clearing.
- Expanded Traffic Logic into Live Decision, Normal Timing, Adaptive Rules, Safety & Test, and Decision History tabs with live active/suppressed/inactive/unavailable rule explanations.
- Added signal policy/status/config/test/preview/history APIs using the existing request-ID/envelope conventions.
- Kept V022 tracking/flow, V021 occupancy, dataset/training/inference/model management, zones, settings/logs, and the prototype-only safety boundary intact.
- Physical public-road traffic control remains disabled.
## 0_2_2 — Cross-frame tracking and flow analytics

- Added a lightweight class-aware centroid/IoU tracker that assigns stable prototype `track_id` values across consecutive detection frames and deduplicates repeated processing of the same source frame.
- Added `counting_line` geometry to the existing camera-aligned Zone Editor. Counting lines use exactly two distinct points and remain analytics-only.
- Added one directional passage event per tracked object/counting-line pair, with `left_to_right`, `right_to_left`, `top_to_bottom`, or `bottom_to_top` direction.
- Added tracked region entry/exit events and completed dwell duration for configured non-ignore polygon regions, including pedestrian waiting-zone dwell summaries.
- Added bounded persistent flow-event runtime storage under `outputs/traffic_flow/events.jsonl`, plus time/class/line/region filters, minute buckets, CSV export, and explicit flow-history clearing.
- Added `GET /api/traffic/tracks`, `GET /api/traffic/flow`, `GET /api/traffic/flow/export.csv`, and `DELETE /api/traffic/flow` while preserving standard request IDs/envelopes and existing occupancy-history APIs.
- Extended live inference detections with optional `track_id`/track age metadata and shows track IDs beside Live AI detection labels.
- Expanded Traffic Analytics with separate Occupancy and Flow / Tracks modes so V021 sampled occupancy is not conflated with V022 unique counting-line passage events.
- Added new stable flow storage errors `ATL-TRAFFIC-007..009` and focused tracking/flow tests.
- Preserved V021 signal-aware simulation, occupancy/counting-region analytics, capture lifecycle, zone overlays, training/inference/model management, settings/logs, and the prototype-only safety boundary.
- The tracker is intentionally lightweight: heavy occlusion, abrupt motion, or crowded same-class crossings can still cause ID loss/swaps. Unique-passage figures apply only to recorded counting-line events, not to all detections seen.
- Physical public-road traffic control remains disabled.
## 0_2_1 — Traffic occupancy analytics and counting regions

- Added persistent detection-backed pedestrian/vehicle occupancy history sampled while the backend runs.
- Added whole-frame pedestrian/vehicle totals and per-region pedestrian/vehicle/combined counts while preserving existing traffic-decision counters.
- Added analytics-only `counting_region` polygons so multiple arbitrary regions can be defined without changing simulation phase recommendation rules.
- Added a Traffic Analytics page with selectable time windows and whole-frame/region scopes, timestamp-aware vehicle/pedestrian trend plots, current/average/peak metrics, busiest-region summary, and simulation phase-change context.
- Added CSV export and explicit traffic-history clear actions. Runtime history is stored under `outputs/traffic_history/` and excluded from source patches.
- Added `GET /api/traffic/history`, `GET /api/traffic/history/export.csv`, and `DELETE /api/traffic/history` with request IDs/logging and stable `ATL-TRAFFIC-004..006` storage errors.
- Extended `GET /api/traffic/state` with whole-frame totals, evaluation/source timestamps, and structured `region_counts`.
- Clarified throughout the app/docs that analytics values are sampled occupancy, not unique passage/flow counts; stable cross-frame object tracking is not implemented.
- Reworked the synthetic camera scene into a persistent signal-aware agent simulation: vehicles remain in horizontal lanes, queue at stop lines when not permitted to enter, and resume on vehicle green.
- Reworked synthetic pedestrians to approach and wait at the curb, traverse the actual zebra crossing only after WALK begins, and finish clearing the crossing before vehicle traffic resumes.
- Added a deterministic 34-second simulation signal cycle (vehicle green, vehicle yellow, all-red, pedestrian WALK, pedestrian CLEAR, all-red) with an on-frame signal/countdown and camera-status signal metadata.
- In simulation mode, `/api/traffic/state.phase` now reflects the exact signal the synthetic agents obey while the detection-driven phase/decision are retained as `recommended_*` metadata for comparison.
- Preserved V020 capture deletion, camera-aligned zones, Live AI zone/signal overlays, and V017 training/inference/settings/logging behavior.
- Physical public-road traffic control remains disabled.
## 0_2_0 — Camera-aligned zones and capture lifecycle

- Added permanent capture deletion from Dataset Capture and Dataset Review. Deleting a capture removes its image, paired metadata, and saved manual-label document.
- Added stable `ATL-DATASET-007` for capture-deletion failures while retaining `ATL-DATASET-003` for missing captures.
- Added `DELETE /api/dataset/captures/{capture_id}` with standard API envelopes, request IDs, logging, and managed-training-dataset staleness reporting.
- Changed Zone Editor to draw polygons directly over the current receiver or simulation frame while keeping the validated 1280×720 reference coordinate system used by traffic counting.
- Added saved-zone overlays to real Live AI camera frames with reference-to-frame coordinate scaling and a Show zones visibility toggle.
- Added a compact simulation-only traffic signal overlay at the top-right of the Live AI canvas.
- Updated version/status surfaces to `0_2_0` while keeping owner-confirmed V017 / `0_1_7` as the passed baseline until owner acceptance.
- Added maintenance hardening while keeping V020 as an unaccepted candidate: backend release surfaces read validated root `VERSION` metadata instead of duplicating release strings, and frontend Dashboard/navigation/fallback surfaces reuse one checked project-version constant.
- Expanded repository checks to validate required release fields, candidate/baseline state, patch/changelog presence, backend version-source use, and current frontend version surfaces.
- Expanded the live backend smoke script to require request IDs and verify health/smoke/template versions match root `VERSION`.
- Added a patch-ZIP validator for `AI_Traffic_Light/` path enforcement, forbidden runtime/generated content, path traversal, and ZIP integrity.
- Reworked AI-agent/developer instructions around the current architecture, candidate acceptance gate, runtime-data preservation, evidence reporting, and changed-files-only packaging; added a concise AI-agent checklist.
- Preserved V017 convergence monitoring, patience-based early stopping, persistent settings/logs, traffic logic, labeling, training, model management, and prototype-only safety boundaries.
- Physical/public-road traffic control remains disabled.
## 0_1_7 — Training convergence, early stopping, and real prototype tools

- Added per-epoch YOLO training metric history for validation fitness, mAP50-95, mAP50, and available train/validation loss totals.
- Added a live Training Convergence SVG plot and best-epoch/plateau counters to the Train / Export page.
- Added configurable `patience` to training requests and forwards it to Ultralytics so training automatically stops when validation fitness stops improving for the patience window.
- Marks convergence-stopped runs as `early_stopped` while retaining the best checkpoint path.
- Replaced the Zone Editor template with a working polygon editor backed by validated persistent `config/zones.json` storage and reset-to-reference controls; runtime zone/settings JSON is locally ignored from Git.
- Replaced mock Traffic Logic with live detection-centre zone counting and an auditable simulation-only phase recommendation.
- Replaced the Settings template with persistent runtime settings for default confidence, Live AI camera-status polling, training patience, and backend log level.
- Replaced mock logs with a bounded real backend log buffer that exposes timestamp, level, module scope, request ID, and stable error code when present.
- Updated Dashboard and navigation/version labels so Project stage is derived from the current backend/smoke version instead of stale hard-coded `0_1_5` text.
- Marked all main PC Studio pages as test-ready prototype surfaces in the page/function registries.
- Added focused training, zone/traffic, settings/logging, and API contract tests plus V017 documentation and acceptance checks.
- Reuses existing `ATL-ZONE-*`, `ATL-SETTINGS-*`, training, inference, and request-validation error codes; no new stable error-code range was required.
- Automatic labeling, model export, device firmware completion, and physical public-road traffic control remain disabled.
## 0_1_6 — Live layout and controllable simulation scene

- Fixed Live AI model/run/path text containment so long trained-model identifiers wrap inside the right-hand model panel instead of overflowing its border.
- Reworked the synthetic camera image around a horizontal road and a vertical pedestrian crossing with horizontal zebra bars.
- Changed synthetic pedestrians to move from the top of the frame toward the bottom while cars/buses move horizontally across lanes.
- Added a larger, varied synthetic population with deterministic scene randomization for positions, speeds, sizes, and counts.
- Added Light / Normal / Busy simulation density presets.
- Added Pause / Resume scene controls so one synthetic frame can be frozen for inspection or persistent dataset capture.
- Added `POST /api/camera/simulation/settings` and extended camera status with simulation density/pause state using existing envelopes, request IDs, Pydantic validation, and stable errors.
- Added `X-Request-ID` to the binary camera-frame response.
- Added focused camera simulation service/API tests and updated V016 documentation, function status, and acceptance checks.
- Preserved V015 model management, confidence/visibility controls, capture, labeling, managed YOLO training, and trained-model live inference.
- Live detections remain prototype/simulation input and do not directly control physical public-road traffic infrastructure.
## 0_1_5 — Model selection, deletion, and live-visibility controls

- Reviewed the trained-model loading path and replaced the latest-only UX with explicit model selection from discovered local `outputs/training/*/weights/best.pt` runs.
- Added backend model-registry functions to list local trained models, persist a default model selection, and delete an outdated model run directory.
- Added a default-model metadata file under `outputs/training/` so Live AI can auto-load the chosen default model after restart.
- Added inference API support for loading a selected/default model instead of only the newest model.
- Extended live detections so the frontend confidence slider is sent to the backend and can go down to 1% for diagnosis.
- Added live visibility controls to show/hide boxes, show/hide labels, and filter visible classes without changing the underlying source frame.
- Implemented a working Model Registry page in the frontend with refresh, load, set-default, and delete actions.
- Updated documentation, error codes, smoke coverage, and local acceptance checks for V015.
- Live detections still do not control zones or traffic signals; automatic labeling, model export, and physical public-road control remain disabled.
## 0_1_4 — Trained-model live inference overlay

- Replaced the inference placeholder with a real Ultralytics-backed service that discovers local `outputs/training/*/weights/best.pt` files and loads the newest run.
- Added model status, load-latest, unload, live-detection, and exact inferred-source-frame endpoints using the existing request-ID/envelope conventions.
- Runs the loaded trained model on the newest receiver or simulation frame and returns class, confidence, and original-image `xyxy` coordinates.
- Caches inference per camera frame so repeated frontend polls do not rerun the same frame.
- Keeps the exact source image used for each detection result so frontend overlays stay aligned even while simulation frames continue moving.
- Upgraded Live AI to automatically load the newest trained model when available, show the real camera/simulation image, overlay boxes, filter displayed confidence, and show inference latency/model state.
- Preserved the original mock Live AI scene as a fallback when no camera frame exists.
- Added trained-model inference service tests, smoke coverage, API documentation, and V014 acceptance checks.
- Live detections do not yet feed zone counts or traffic-light decisions; automatic labeling, model export, and physical public-road control remain disabled.
## 0_1_3 — Manual labeling and managed YOLO dataset

- Replaced the Dataset Review placeholder with a working captured-frame browser and manual bounding-box label editor.
- Reused the shared six-class schema: person, car, bus, truck, motorcycle, and bicycle.
- Added persistent label JSON files under each capture session without altering the original image or capture metadata.
- Treats a saved zero-box review as a valid negative example and keeps unreviewed captures distinct.
- Excludes captures tagged `bad` from managed training builds.
- Added a deterministic managed YOLO train/validation builder at `datasets/yolo/` with image copies, normalized `.txt` labels, `data.yaml`, and a manifest.
- Requires at least two reviewed non-bad frames so train and validation sets are distinct.
- Detects label changes after a dataset build and marks the managed dataset stale until rebuilt.
- Connected the existing Train / Export page to the managed `yolo/data.yaml` status while preserving support for other labeled YOLO YAML files inside `datasets/`.
- Added labeling/build API contracts, stable dataset error codes, service tests, and acceptance documentation.
- Automatic labeling, live YOLO inference, model export, and physical public-road traffic-light control remain disabled.
## 0_1_2 — Persistent capture and optional labeled-dataset training

- Replaced the Dataset Capture placeholder with a working receiver/simulation capture page.
- Added atomic image and paired JSON metadata writes under `datasets/captures/<session>/`.
- Changed synthetic simulation frames to PNG so they can be saved by the same capture path as device images.
- Added persistent capture counts, session IDs, quality tags, notes, stable envelopes, and request IDs.
- Added a real optional Ultralytics YOLO background runner with dataset-path/config validation and status polling.
- Added frontend capture/training controls, strict mutation error handling, tests, and generated-data ignores.
- Raw captures remain unlabeled; real detection training requires a prepared YOLO dataset and the optional training dependency.
- Real inference, automatic labeling, model export, and physical traffic-light control remain disabled.
## 0_1_1 — Camera frame receiver and simulation

- Added an in-memory PC-side endpoint for ESP32/Raspberry Pi JPEG or PNG frame uploads.
- Added latest-frame metadata, stale-frame detection, and an image response endpoint.
- Replaced the Camera Sources placeholder with an automatically refreshing preview and receiver status.
- Added a moving synthetic camera mode that tests the same viewer path without camera hardware.
- Added stable camera validation errors and documented the upload contract.
- Updated Windows backend launchers to listen on the local network for future camera-node uploads.
- Real AI inference, training, and physical traffic-light control remain disabled.
## 0_1_0 — PC Studio test-ready mock version

- Promoted the PC Studio template from layout-only to a local smoke-testable mock version.
- Added backend smoke-test endpoints and backend self-check script.
- Added frontend/backend status display, refresh flow, and mock API integration checks.
- Updated visible version labels from 0_0_4 to 0_1_0.
- Added human testing instructions and a test-ready checklist.
- Still intentionally excludes real YOLO inference, real camera capture, training, model export, and physical public-road control.
## 0_0_4 — PC Studio app template and function map

- Added the first structured PC Studio frontend template.
- Added sidebar navigation and placeholder pages for all planned main functions.
- Added reusable layout, placeholder, metric, checklist, and status components.
- Added central frontend page and function registries.
- Added backend placeholder route modules for camera, inference, zones, dataset, training, model registry, settings, logs, and template metadata.
- Updated backend app wiring to expose the placeholder API structure.
- Expanded error-code ranges for future camera, inference, zone, dataset, training, model, settings, logs and template metadata.
- Added human/AI documentation for confirming the PC Studio function list and GUI layout before real implementation.
## 0_0_3 — Modular code, API contracts, logging, and error codes

- Added coding standards for small, debuggable modules.
- Added backend logging/error-code infrastructure.
- Added frontend API/debug logging helpers.
- Refactored placeholder backend routes into smaller route/core/service modules.
- Added documentation for API contracts, debugging, logging, and error-code ranges.
- Added patch notes for **0_0_3**.
## 0_0_2 — Human and AI-agent instruction docs

- Added root-level `AGENTS.md` for AI agents and coding assistants.
- Added `docs/AI_AGENT_GUIDE.md` with detailed AI development protocol.
- Added `docs/HUMAN_GUIDE.md` with human-facing usage, upload, patch, and safety instructions.
- Updated README documentation links.
- Updated version metadata to **0_0_2**.
## 0_0_1 — Documentation and version cleanup

- Corrected project wording from the earlier “Version 1 / 0.1.0” draft to the chosen **0_0_x** versioning scheme.
- Updated README layout references from `AI_Traffic_Light_v1/` to `AI_Traffic_Light/`.
- Added clear baseline/patch distinction:
  - `0_0_0` = initial skeleton.
  - `0_0_1` = documentation/version cleanup.
- Updated documentation roadmap and versioning notes.
- Updated placeholder UI/backend version labels to avoid old version naming.
## 0_0_0 — Initial starter skeleton

- Added monorepo project structure.
- Added PC Studio backend placeholder.
- Added ESP32-CAM firmware placeholder.
- Added shared schemas.
- Added documentation and roadmap.
- Added sample fake detection data.
- Added Windows helper scripts.
