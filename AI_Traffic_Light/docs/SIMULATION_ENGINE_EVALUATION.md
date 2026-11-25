# Simulation and rendering engine evaluation — Update 20 / S01

Date: 25 November 2026. Evidence categories: upstream documentation, source inspection, executed offline tests, blocked external engine execution, proposed validation. No field data.

## Current ownership and problem

`camera_frames.py` owns selected source, synthetic camera rendering, simulation state and time; its constructor seeds from wall-clock time, and existing read paths refresh the simulation. The OpenCV PNG and 1280×720 camera coordinates serve detector, capture and region workflows. `network_simulation_experiments.py` is a separate seeded, queue-based comparison service. `SimulationCamera3D.tsx` polls the shared scene and renders the existing presentation. Do not conflate these with a unified microscopic road engine. The existing protected signal phase service and explicit conflict interlock must remain the decision authority.

## Qualitative comparison (external documentation; no performance ranking)

| Traffic candidate | License and setup | Capability and integration | Decision |
|---|---|---|---|
| Existing Python/OpenCV and queue experiment | Existing dependencies; no new install | Current camera compatibility; separate simplified motion and queue models; wall-clock seeded live scene | Retain as reference and fallback |
| Eclipse SUMO | EPL-2.0; GPL-2.0-or-later secondary option subject to license conditions; official Windows distributions | Microscopic vehicle and pedestrian simulation, lane networks, explicit step control, seeded randomness, Python TraCI; subprocess and serialization overhead to measure | Preferred evaluation target; no adoption yet |
| CityFlow (cityflow-project/CityFlow) | Apache-2.0; upstream Windows guidance recommends WSL/Docker | Vehicle-focused microscopic network simulation, Python API; equivalent pedestrian crossing and native Windows integration not established from reviewed docs | Defer; reconsider if comparable pedestrian support and setup verified |

| Rendering candidate | License/setup | Integration considerations | Decision |
|---|---|---|---|
| Existing scene renderer | Already in React app | Current UI/camera projection retained; baseline performance not measured | Keep fallback |
| Three.js | MIT; npm/Vite integration; WebGL capability required | Explicit geometry, cameras and transforms; scene lifecycle, disposal and context-loss handling under app ownership | Preferred evaluation target for small modular renderer |
| Babylon.js | Apache-2.0; npm integration | Full-featured WebGL/WebGPU engine; broader engine surface, no measured size/performance disadvantage asserted | Viable alternative; defer pending matched comparison |

The decision favors documented domain fit and integration separation, not measured speed. SUMO's native signal program is acceptable for the isolated smoke scenario only. In shadow mode M.E.S.H. must provide bounded virtual movement permissions through the adapter; never duplicate signal authority or connect to physical lamps. TraCI single-client explicit fixed steps first; libsumo only after profiling, reviewing its process/thread restrictions and verifying error/cleanup semantics. Three.js receives immutable scene snapshots and interpolates only visual positions; rendering must not advance traffic time, mutate agent lifecycles or imply a calibrated camera. Keep synthetic detector/capture projection until validated; preserve all source IDs and API contracts.

## Reproducible first smoke scenario

The optional `scripts/evaluate_simulation_engine.py` uses only the Python standard library, creates temporary XML files and invokes locally installed SUMO tools via argument arrays and finite timeouts. No automatic install or networking. One four-arm junction (100 m arms), eight directed edges with 2 m sidewalks, one lane per direction, 10 m/s speed limit; 12 passenger vehicles and 12 walkers, every 5 s from t=0 to 55 s. Seed 42, 0.2 s steps, 180 s horizon, two identical runs; generated crossings, generated native signal plan; teleport disabled. Fixture is deliberately synthetic and is not a calibrated Hong Kong road, comparative control experiment, or evidence of safety. The smoke criterion requires all 12 IDs of each type observed and exact repeatability of canonical time/ID/x/y/speed traces on the same engine/version/settings. It does not verify completion, absence of collision, physical pedestrian clearance, crossing use or determinism across versions/platforms. Generated network and pedestrian path must be visually and topologically checked before relying on it. Per-run wall time includes engine startup and file output; not isolated step latency. No memory or GPU measurement is implemented in this harness. Only summary digests and counts are retained by default; temporary raw traces are discarded. Exit 0 pass, 1 fail, 2 blocked (missing executables).

```powershell
# From AI_Traffic_Light, no optional dependencies needed for these checks
python scripts/test_v0564_engine_evaluation.py
python -m py_compile scripts/evaluate_simulation_engine.py scripts/test_v0564_engine_evaluation.py
# Optional: only after vetted SUMO installation, with sumo and netconvert on PATH
python scripts/evaluate_simulation_engine.py --output "$env:TEMP\mesh-sumo-evaluation.json"
```

## Executed evidence

Actual local evidence (25 November 2026): Python 3.13.5, Linux x86_64; three offline unittest cases passed and both Python files compiled. The real harness ran and returned exit 2 / blocked with zero trials because sumo and netconvert were absent from PATH; no TraCI, libsumo or CityFlow package installed. GitHub checkout DNS failed; no full local checkout or renderer test. Exact staged Git blobs: harness 448f17187d9c7afcf216438e0915de92f7cb3411, test 81c629182523bd8675d2a5921f0c028d9c754925. Prior full CI passed ([45601046778](https://github.com/henrywork059/AiTL/actions/runs/45601046778)); new CI and owner PASS pending. No measured third-party engine performance or physical validation.

Actual harness outcome: {"status":"blocked","reason":"Missing executables on PATH: sumo, netconvert","seed":42,"step_s":0.2,"duration_s":180,"runs":[]} (excerpt). Do not substitute synthetic trace parser fixtures for executed SUMO runs.

## Adoption gates and follow-on benchmarks (proposed)

1. Install a vetted, pinned Windows release from upstream in an isolated environment (not the production requirements). Verify `sumo --version`, `netconvert --version`, tool license/notice, checksums, Python/TraCI compatibility and both traces; investigate any missing persons, warnings, collisions, invalid routes or nonmatching output.
2. For a fair performance comparison, construct equivalent lane topology, arrivals and virtual phase permissions for current reference and shadow engine. Record versions, OS/CPU/RAM, seed list (42, 43, 44), fixed step, scenario geometry, number of agents, warm-up and at least three repetitions; record p50/p95 step latency, wall time, CPU and peak resident memory, arrivals/completions, queues/wait, crossing/teleport/collision diagnostics. Do not compare uncalibrated queue-model outputs as equivalent microscopic trajectories. Targets must be justified after measuring baseline.
3. Renderer benchmark on the same Windows browser/GPU/resolution and immutable recorded snapshots at 10/100/500 agents; compare existing renderer, Three.js and optionally Babylon.js with fixed camera and equivalent geometry; record median/p95 frame time, dropped frames, context loss, memory and cleanup over repeated mount/unmount. A 30 fps working target (33.3 ms/frame) is proposed, not measured. Check accessibility, vehicle/person lifecycles, and camera projection. No CDN runtime dependency; pin and review any npm addition.
4. Existing npm ci reported two high-severity vulnerabilities in 19a. New CI audit evidence step reports advisory details without auto-fixing dependencies; audit is non-blocking for this no-adoption candidate only, and not a security PASS. Resolve findings or document explicit owner-approved residual risk before adopting packages. No npm audit fix --force.
5. Update 21 defines reset/step/pause/snapshot/seed against the existing engine; Update 22 shadow integration requires real-engine smoke, reviewed dependency security and rollback. Keep the old engine default until parity and owner acceptance. No real signal commands.

## Upstream references (reviewed 25 November 2026)
- SUMO overview and licensing: https://sumo.dlr.de/docs/Downloads.php ; https://sumo.dlr.de/docs/Installing/
- SUMO randomness and explicit step/Python interfaces: https://sumo.dlr.de/docs/Simulation/Randomness.html ; https://sumo.dlr.de/docs/TraCI/Interfacing_TraCI_from_Python.html ; https://sumo.dlr.de/docs/Libsumo.html
- SUMO pedestrian geometry, XML and trace output: https://sumo.dlr.de/docs/Simulation/Pedestrians.html ; https://sumo.dlr.de/docs/Networks/PlainXML.html ; https://sumo.dlr.de/docs/Simulation/Output/FCDOutput.html ; https://sumo.dlr.de/docs/sumo.html
- CityFlow upstream license and Windows guidance: https://github.com/cityflow-project/CityFlow ; https://github.com/cityflow-project/CityFlow/blob/master/docs/source/install.rst
- Three.js license, renderer, integration: https://github.com/mrdoob/three.js/blob/dev/LICENSE ; https://threejs.org/docs/pages/WebGLRenderer.html ; https://github.com/mrdoob/three.js/blob/dev/manual/pages/installation.html
- Babylon.js overview and license: https://github.com/BabylonJS/Babylon.js ; https://github.com/BabylonJS/Babylon.js/blob/master/license.md


## Follow-up: Update 21 security audit and clock foundation

Security gate: previous CI audit JSON (run 45619974507, 25 Nov 2026) identified two high-severity vulnerable packages: locked source-map-js 1.2.1 ([GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), patched range starts at 1.2.2) and direct Vite 8.2.1 ([GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm), audit suggested Vite 8.3.8; additional lower-severity Vite advisories listed in the CI log). The audit step is non-blocking, exited 1, and is not a security PASS. No dependency changes here; package remediation requires regenerated lockfile and fresh audit/build/test evidence. Restrict prototype development server to trusted local access; do not expose it to untrusted networks or open untrusted projects/source maps. Security remediation takes priority before new dependencies; real SUMO smoke and security gates remain blockers for Update 22.

CameraFrameService delegates timing to a small LegacySimulationAdapter under the existing owner lock. Elapsed monotonic time is represented in integer nanoseconds, accumulated and committed only in 50 ms steps; the old per-refresh fractional step is eliminated. The adapter exposes reset, explicit step, sync, pause, stop and immutable clock snapshot (time, pause, seed). The existing service retains world initialization, seeded RNG, agent movement, render/cache, observation identity and protected signal rules. One existing phase evaluation is shared by both movement types per committed step. Optional constructor-only seed and monotonic clock injection enable reproducible tests without changing HTTP endpoints; production retains the wall-clock-derived default seed. Existing private clock fixture seam is forwarded to the adapter. No new dependencies or physical outputs.


## Dependency remediation trial

Preparation 21a (same candidate, no package or runtime changes): [0_5_65 CI 45621580527](https://github.com/henrywork059/AiTL/actions/runs/45621580527) passed the complete offline suite, including all four V0565 scheduler/agent tests, frontend regression, typecheck and build. Its non-blocking audit still reports two high-severity vulnerable packages and exit 1. Local npm registry DNS resolution failed; integrity metadata and regenerated lockfile cannot be guessed. A feature-branch-only, read-only Windows CI trial resolves Vite 8.3.8 and an exact source-map-js 1.2.2 override using npm, emits the generated manifests for inspection, verifies installed versions, tests frontend compatibility and runs a blocking high-severity audit. The trial never commits, publishes or changes the existing candidate's lockfile. Review the generated dependency diff and CI evidence before an atomic 0_5_66 remediation candidate; retain the current owner-accepted baseline. Update 22 remains blocked by security and real SUMO smoke.
