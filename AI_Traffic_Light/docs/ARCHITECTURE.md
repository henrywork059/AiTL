# Architecture

## Physical ESP camera path

```text
ESP32-CAM / OV2640 A                    ESP32-CAM / OV2640 B ...
  FB1 + CAMERA_GRAB_LATEST                FB1 + CAMERA_GRAB_LATEST
  PSRAM JPEG framebuffer                  PSRAM JPEG framebuffer
  Wi-Fi sleep disabled                    Wi-Fi sleep disabled
  HTTP control :80                        HTTP control :80
  binary TCP JPEG :81                     binary TCP JPEG :81
          │                                       │
          ▼                                       ▼
   RemoteCameraService                     RemoteCameraService
   independent worker/socket               independent worker/socket
          └───────────────┬───────────────────────┘
                          ▼
                 RemoteCameraManager
                 saved per-camera profile
                 newest-frame cache/source
                 one selected active source
                          │
                          ▼
                  CameraFrameService
                    shared active frame
                          ├── /api/camera/live.mjpeg browser relay
                          ├── Live AI
                          ├── Dataset Capture
                          ├── Zones / tracking
                          ├── traffic state / analytics
                          └── Junction Network observation source
```

HTTP port 80 is used for ESP status/config/start/stop control. After Start Stream, each ESP-to-PC image path is one persistent length-prefixed TCP JPEG stream on port 81. Browser clients do not connect directly to the ESP image socket; PC Studio relays the selected shared frame as MJPEG.

The production V0310 tuning keeps one framebuffer. On the normal PSRAM path it uses `CAMERA_GRAB_LATEST` and preserves the existing `ATL1` wire format while replacing the inherited vectored hot-path write with bounded plain `send()` progress capped at 11,680 application bytes per outer write. TCP/lwIP remains responsible for actual packet segmentation. Saved Camera Sources frame size, JPEG quality and target FPS remain authoritative.

Multiple saved ESP sessions may stream concurrently. Each session has an independent worker and newest-frame cache, but exactly one saved ESP is selected to feed the existing shared capture/tracking/traffic pipeline. Each accepted ESP packet is validated once into an immutable CameraFrame with a process-unique frame number and original PC receive time. Switching source clears the previous physical frame first and promotes the same cached frame only when it is recent; selection and background inference use identical source/time/frame identity. Frame numbers may move backward when switching sources; a selection change is not a new observation. Replacing a saved IP retires the previous session generation, so a late frame from that worker is ignored even if the source ID is reused.

If an ESP stream drops or the device reboots, its session can recover using the retained configuration. Recovery serializes status/config/start with replacement session control and checks worker event ownership before publishing state; a request already issued can finish before replacement control. Retired workers cannot publish subsequent failure/frame metadata to a replacement session. Explicit stop/disconnect/restart/re-address retires delivery and clears only the affected source cache. Background AI uses source epoch and simulation mode tokens to reject obsolete result publication/read/forwarding; unexpected transport loss still uses the existing freshness expiry. The stop helper retains its bounded join. An in-progress external frame-sink callback is not rolled back. Simulation temporarily suspends physical image transfer while retaining saved profiles/session intent, and physical streams resume afterward.

## V0554 device capability projection

`RemoteCameraManager` remains the sole saved-camera registry and runtime session owner. Its existing `status()` operation collects current per-source ESP/simulation summaries and uses pure `device_capabilities.project_camera_device()` to derive an additive, read-only contract for each saved source and the selected source. The versioned descriptor exposes software input support, current freshness/health, and explicitly unavailable lighting/speaker outputs. It is not stored in `remote_cameras.json` or copied into inference/traffic state. It does not probe ESP hardware, create sessions or permit physical outputs. Existing PC-owned control, original-frame timestamps and source-generation guards remain unchanged; the full selected top-level legacy status is not an atomic camera-switch snapshot.

## V0555 camera setup status coherence

The manager performs the existing optional network probe without holding the registry lock, then derives the returned selected profile, current session status, cached frame and capability contract under one selection snapshot. The UI ignores obsolete poll results during/after an action, validates drafts before sending a request, and gates preview/selected-source controls on current source identity and fresh observations. Existing registry and transport ownership remain unchanged. This is not a multi-client command lock or synchronized sampling of all cameras.

## V0556 isolated fake bench output boundary

`bench_output.py` defines a disabled-by-default controller and fake in-memory adapter with bounded command lease, correlated acknowledgment, monotonic expiry, explicit off and disconnect. Connection-generation changes invalidate prior arming even when no watchdog tick observed the intervening disconnect. It is not instantiated by live application routes or signal control. No camera, registry, firmware or physical output path changes. The local explicit arm gate is only a test-harness gate. The fake watchdog is checked on operations and explicit tick; a real actuator would need independent watchdog, authorization and electrical safety validation.

## V0557 synthetic lighting preparation

`bench_lighting.py` provides an isolated synthetic binary pulse facade over the existing `BenchOutputController`. It owns no independent lease or arming state. The test-only status projection identifies synthetic lighting separately from physical device availability. Existing camera registry, physical capability projection and traffic logic remain unchanged. Physical integration is BLOCKED: lighting model, voltage/current requirements, driver/electrical interface and controlled-bench authorization remain unconfirmed; an independent hardware fail-safe is not implemented. No physical testing or electrical safety validation was performed.

## V0558 synthetic speaker preparation

`bench_speaker.py` wraps the existing `BenchOutputController` with a fixed synthetic notice catalog and normalized volume metadata. A local lock keeps notice metadata consistent with facade operations; the existing controller remains the sole owner of arming, lease and acknowledgment state. Status/tick clears stale metadata and never generates audio. No change to the camera registry, physical capability projection or signal control. Physical speaker integration is BLOCKED: hardware model, amplifier/driver, electrical specifications, acoustic limits, independent hardware fail-safe and controlled-bench authorization remain unconfirmed or unavailable. No acoustic or physical safety validation was performed. Physical lighting also remains blocked.

## Synthetic camera render caching

`CameraFrameService` renders a 1280 × 720 BGR canvas and encodes the canonical simulation PNG once per tick. Mirrored simulation cameras B/C/D flip that same current-tick render and encode their own PNGs; they do not decode the canonical PNG. The bounded canvas cache occupies approximately 2.6 MiB and is discarded when simulation resets, stops or resumes. Existing per-view PNG caching, simulation scene coordinates, camera APIs, and protected virtual signal rules are unchanged. This optimization does not affect the real ESP transport or permit physical traffic-light control.

The simulation integrator advances agents in at most 50 ms substeps (with a maximum 2 s catch-up per update). For each substep it queries the **existing** `SignalRulesService.signal_state` exactly once and passes that same protected phase to the vehicle and pedestrian movement helpers. The query may advance stateful phase/scenario logic; it is not a pure clock lookup. Sharing one snapshot avoids duplicate evaluations at identical simulation times and keeps both agent types on the same signal decision. The signal controller still owns all phase transitions, minimum clearances and scenario rules; no new controller or physical output is added.

## Junction Network observability path

V0311 adds a configuration/observability layer over the existing source and topology services:

```text
config/intersections.json
  junction identity
  node position
  directed links
  source_ids[]
  primary_source_id
          │
          ▼
IntersectionNetworkService
          │
          ├── source → junction resolution
          ├── topology context
          └── persisted layout / camera assignment
                          │
RemoteCameraManager ──────┤ camera health / selected source
CameraFrameService ───────┤ current shared frame source
traffic state ────────────┤ current vehicle/pedestrian/decision data
                          ▼
             JunctionNetworkOverviewService
                          │
                          ▼
           GET /api/traffic/network/overview
                          │
                          ▼
               JunctionNetworkPage
               nodes / lines / load
               cameras / events / warnings
```

One junction may own several camera/source IDs. A source ID remains exclusive to one junction so source-to-junction identity is unambiguous. The overview service is observational: it does not start cameras, run inference, arbitrate signals, or create extra controller instances.

Only the junction resolved from the **currently shared selected camera/simulation source** receives current live traffic/decision values. Other configured junctions show topology and camera health but explicit unavailable traffic observations. This prevents a multi-camera registry or visual network from being misrepresented as simultaneous multi-junction AI fusion.

## Safety and capability boundary

The multi-camera input architecture and Junction Network page are foundations for later live multi-intersection work. They do **not** currently provide:

- simultaneous independent traffic-controller pipelines for all junctions;
- cross-camera object identity or physical transfer matching;
- live emergency-vehicle recognition/priority;
- active public-road signal control.

Network cooperation, pedestrian-aware, vehicle-class and emergency-priority behavior retain their documented simulation/evidence scope unless a later explicit live implementation changes that boundary.

## V059 global AI preview

`RemoteCameraManager.frames_for_inference()` snapshots the newest fresh JPEG from every saved connected ESP source and each saved simulated camera; it also supports recent receiver uploads. `MultiCameraInferenceService` runs as one background worker under FastAPI lifespan, sequentially serving all feeds with the one globally loaded inference model. The persisted `inference_interval_ms` targets a *complete pass* over available cameras (best effort, not guaranteed per-camera throughput). No frame backlog is queued. Latest inference results are cached by camera ID and stale observations suppressed. Preview selection reads results via `/api/inference/cameras/{source_id}` and uses existing side-specific crosswalk polygons for per-frame counts. Physical/network signal control and legacy selected-source traffic, tracking and capture remain unchanged. Do not sum Side A/B results as unique objects without identity fusion.

## V0510 Network signals and shared rule settings

Traffic Light Settings and Live Signal Adjustments both edit the existing persisted `signal_rules` config. The former changes only default phase durations in the active profile; the latter configures disabled-by-default ranked scenarios. The existing protected phase controller handles requests. `phase_remaining_seconds` is derived from the current protected phase and can be used in crossing-clearance scenarios.

Network's `CrosswalkSignalIndicators` uses only the shared simulation signal status associated with the current observed source. Connected neighbours receive a read-only notice, **not** a commanded phase. Crosswalk topology currently lacks conflict relationships and per-crosswalk controller instances; actual connected-crosswalk coordination is not implemented.

## V0511 independent crosswalk controller registry

`CrosswalkSignalService` indexes independent `SignalRulesService` runtime instances by stable saved crosswalk ID. The controller instances share the existing persisted rule configuration and protected phase sequence but not phase clocks, decisions, incidents or observation buffers. The read-only API and Network signal indicators consume keyed state. The existing global signal runtime continues to serve legacy camera simulation and traffic endpoints. Future crosswalk-local observation/coordination interfaces must add camera source ownership and verified movement conflicts before active neighbor signal changes. No physical actuation.

## V0512 automatic Crosswalk AI inference bridge

The existing background `MultiCameraInferenceService` feeds its latest per-camera inference snapshot to `CrosswalkSignalService.ingest_camera_results`, independent of active UI page. `crosswalk_observations.py` maps saved Crosswalk camera source IDs to geometry by side, counts each class with the bottom-center object point, combines physical region counts from synchronized cameras by average, and produces crosswalk-qualified region count keys. A per-crosswalk frame signature prevents repeatedly refreshing a frozen frame; missing/stale sources invalidate observations. Camera-derived adaptive observations are additionally aged from the original receive timestamp (oldest contributing view for fusion), capped at five seconds or the configured shorter timeout. Interrupted persistence resets, and named classes absent from all observed regions are unavailable rather than assumed zero without verified model capability. New adaptive actions are suppressed on expiry while committed phase timing and protected transitions remain intact. This feeds class-based scenarios to the isolated **simulation** controllers. No movement-role semantic inference, physical control, or adjacent controller arbitration is introduced.

A virtual-preview mode also accepts real ESP camera AI when global camera simulation is off; it runs only software signal models, resets when switching from simulation, expires when fresh detections stop and labels the resulting signal `virtual` rather than physical. No ESP signal controller command is generated.

## V0512 simulation-only emergency corridor follow-up

The existing source-aware per-crosswalk observations can confirm an ambulance-class object across distinct inference frames. An explicitly configured one-hop directional Network link then asks the destination's independent virtual signal controller to extend its current/next protected vehicle-green phase. The rule preserves minimum pedestrian WALK/CLEAR and amber/all-red phases and expires if unserved. Without a route it remains inactive. No physical outputs or verified crosswalk movement-conflict matrix.

## V0514 crosswalk Network virtual movement interlock

Existing independent `CrosswalkSignalService` instances receive their assigned camera detections as before. Saved `network.links[].movement_conflicts` explicitly expresses unsafe source/destination movement pairs. A small pure `crosswalk_signal_coordinator` schedules compatible **virtual** movement permissions, pauses the blocked crosswalk's local simulation clock, projects virtual red holds and enforces a 2 s gap after a conflicting virtual grant ends. Clearance history survives a compatible new grant; closely spaced different releases conservatively protect both movements. Standalone contradictory lamps are sanitized. Emergency confirmation requires distinct fresh same-source frame IDs with at least one second separation; pending priority is withdrawn when the confirming evidence or route is no longer valid, without retroactively shortening committed phase durations. Emergency route priorities are requested through the existing protected local phase mechanism and require an explicitly configured movement conflict. Network displays projected signal state and hold reason; physical outputs are not implemented. Dynamically introducing conflicts during a running simulation can cause virtual red clamping and must not be treated as certified traffic safety.


### Internal observation identity (0_5_59 candidate)

Internal immutable `ObservationIdentity` projects the existing camera frame's original source ID, PC receive timestamp, frame number, original image dimensions and provenance. Managed ESP frames carry the existing session generation and source retirement epoch; synthetic primary/mirrored frames carry the render's mode generation. Ordinary HTTP uploads are unverified external input. Selected cache promotion retains the same frame and identity. The inference cache uses the shared frame key without changing its semantics. Existing manager lifetime/freshness checks, public JSON, crosswalk detection dictionaries, source coordinates, and selected-source control boundary remain unchanged. Generation metadata records acquisition, not current eligibility; the manager's existing token remains authoritative. Recent valid cached physical frames may still be restored after mode switches with original identity/time, not re-timestamped. No simultaneous multi-junction fusion, physical output or firmware change.


### ATL1 transport ownership (0_5_60 candidate)

Extract the existing ATL1 packet value, exact-length socket wrapper, encoder and decoder into `camera_tcp_transport.py`. The extracted class/function bodies are unchanged. `RemoteCameraService` imports the same symbols at its existing compatibility and monkeypatch seams; it retains socket opening/configuration, worker ownership, stop/join, cancellation, recovery, control requests and frame publication. `RemoteCameraManager` remains the sole registry/session-selection owner. No new transport, duplicate parser, API change, wire change, physical output or freshness policy change.


### Selected-source tracking scope (0_5_61 candidate)

The existing selected-source tracker now uses an internal scope of camera ID, explicitly matched junction (unmapped remains None), original image dimensions, provenance and acquisition generation/epoch. A scope change, frame-number reset or gap over five seconds starts new tracks; no identity is carried between sources or junctions. A bounded 256-source watermark prevents previously processed cached frames from advancing tracking after switching or active reset. Current same-frame threshold requests may annotate without advancing. Live callers supply immutable ObservationIdentity; expired/mismatched frames receive no tracking annotation, and tracking status endpoints suppress non-current scopes. The existing per-source frame timestamp and five-second freshness policy are reused. No inactive tracker continuation, new inference pipeline, cross-camera fusion, signal policy changes or new public fields. Existing flow events remain legacy aggregate history; independent traffic observation/flow semantics are next in Update 18. Watermarks are process-local and bounded, and an evicted source loses its replay history; no global unique-vehicle claim.


### Source-qualified traffic observations (0_5_62 candidate)

Selected-source analytics now preserve original source ID, explicit junction mapping, acquisition timestamp/frame and provenance in newly recorded flow events. Flow JSON returns per-source/junction/provenance summaries without cross-camera summation; historical aggregate records remain readable with unknown attribution. The additive traffic_observation projection reports sampled region occupancy, stationary waiting candidates and unavailable state with null metrics. The queue heuristic uses an 8-reference-pixel radius for at least 1000 ms in a configured waiting/queue zone, not calibrated speed or a verified traffic queue. New occupancy history samples retain attribution. Existing aggregate summaries, CSV columns, zones, selected-source architecture and virtual signal authority remain unchanged.

No simultaneous tracking or independent live observations for inactive sources; no unique-object fusion. Stationarity is sampled image-space evidence; unconfirmed objects may still be waiting, and region geometry/calibration are user configured. Lifetime is checked before tracking and before persistence/projection; concurrent source switching and inference remain nontransactional. Existing aggregate history and CSV retain legacy semantics. External uploads are not verified ESP observations. Physical lighting/speaker and actual ESP measurements remain blocked/outstanding.


### Frontend polling and request cancellation (0_5_63 candidate)

The existing useSerialPolling hook delegates single-flight task ownership to a small tested pollingScope core. Committed scope changes, disabling and unmount retire an AbortController; the current in-flight promise remains owned until settlement. Retired errors are suppressed, and migrated callers use isCurrent before publishing. apiClient propagates cancellation without logging it as a transport failure or substituting fallback data, preserving genuine API error codes/request IDs and legacy fallback behavior for other callers. Analytics reads use strict typed requests, filter-keyed results and explicit unavailable display; camera AI preview scopes by camera and active model; dataset label reads cancel on capture changes. No new dependencies, endpoints, backend, UI redesign or signal changes.

Cancellation is client-side and does not guarantee the server stops work. Existing zero-argument polling callers retain their legacy publication behavior until individually migrated; scope retirement suppresses hook-level errors but cannot prevent an unguarded callback from writing. AI preview context polling guards publication but its three underlying reads are not aborted. Genuine errors in analytics now show unavailable rather than fallback zero (intentional behavior correction). Full browser rapid-navigation, React lifecycle and owner Windows/ESP checks remain outstanding. No physical output authorized.


### Simulation engine evaluation (0_5_64 candidate)

Update 20 / S01 documents the conditional choice of Eclipse SUMO (external process, eventual single-client TraCI adapter) for microscopic traffic and Three.js (WebGL renderer) for presentation. Added a standalone standard-library Python evaluation harness that generates a synthetic four-arm signalized junction and identical seeded vehicle/pedestrian demand, runs two optional SUMO CLI trials and compares normalized position traces. The current simulator, protected signal controller, camera routes, existing network experiment service and production renderer remain unchanged. No SUMO, TraCI, Three.js or other new dependency installed or adopted.

Engine choice is conditional, not adoption. Before shadow integration, run the optional smoke scenario on a pinned Windows SUMO distribution and validate pedestrian path/crossing geometry, both traces and error handling. Before dependency adoption, inspect existing npm high-severity findings and proposed dependency tree, verify licenses and versions, and document remediation or explicitly accepted residual risk. Compare matched traffic and render workloads; retain rollback, independent safety rules and no physical actuation. No throughput, CPU/RAM, GPU, latency or safety superiority has been demonstrated. Update 21 can proceed with the existing simulator adapter and deterministic clock without new dependencies; Update 22 must wait for engine and security gates.

See [evaluation decision and protocol](SIMULATION_ENGINE_EVALUATION.md).


### Fixed-step legacy simulator adapter (0_5_65 candidate)

CameraFrameService delegates timing to a small LegacySimulationAdapter under the existing owner lock. Elapsed monotonic time is represented in integer nanoseconds, accumulated and committed only in 50 ms steps; the old per-refresh fractional step is eliminated. The adapter exposes reset, explicit step, sync, pause, stop and immutable clock snapshot (time, pause, seed). The existing service retains world initialization, seeded RNG, agent movement, render/cache, observation identity and protected signal rules. One existing phase evaluation is shared by both movement types per committed step. Optional constructor-only seed and monotonic clock injection enable reproducible tests without changing HTTP endpoints; production retains the wall-clock-derived default seed. Existing private clock fixture seam is forwarded to the adapter. No new dependencies or physical outputs.

This is a legacy scheduling adapter foundation, not a complete replacement engine. Same seed and elapsed schedule with equivalent phase inputs and no gap over the two-second catch-up bound produce the same committed movement steps; elapsed time above that bound is deliberately discarded, and pause transitions discard uncommitted time since last sync as before (already accumulated substep remainder is retained). Live progression is still demand-driven; it is not an independent background worker, and existing adaptive rule evaluations and evidence expiry still use real time. Scene clock/agents and 2 Hz cached PNG may differ within a render tick; existing API semantics and source IDs are unchanged. Agent lifecycles, renderer, network experiments, and policy are unchanged. The internal clock adapter is only invoked by the camera owner in enabled mode; stop is not an external command interface. No SUMO execution or physical safety claim.


### Frontend security remediation (0_5_66 candidate)

Publish the exact package.json and package-lock.json generated by the read-only Windows dependency trial on parent ccfdc0c86f98e5a76715f16d99f2e083639f802c. Vite 8.2.1 → 8.3.8 (exact direct pin); source-map-js 1.2.1 → 1.2.2 (exact transitive override). Vite's dependency closure also updates Rolldown and its native bindings 1.2.4 → 1.2.19, @oxc-project/types 0.144.0 → 0.156.0, PostCSS 8.5.26 → 8.5.33, nanoid 3.3.18 → 3.3.20, and picomatch 4.0.5 → 4.0.7. Eight optional lock entries added (including WASM/Android bindings, optional @emnapi beta runtime/core, support packages); none removed. Lock entries 68 → 76 including root. Other direct package versions unchanged (React/React DOM 19.2.8, TypeScript 7.0.2, @vitejs/plugin-react 6.0.5). All resolved entries use npm registry HTTPS and SHA-512 integrity. No new app functionality, API, simulator or physical-control changes. Make high-severity npm audit blocking in standard CI; no automatic fixes or force updates.

Audit results are time-specific and do not establish absence of all vulnerabilities. Optional WASM/Android packages (including two pre-release @emnapi packages) are part of the resolver's optional dependency closure, not exercised by the Windows native build. Other platform compatibility, runtime browser/Windows/ESP owner acceptance remain unverified. Remaining direct manifest 'latest' entries retain the existing lock behavior; use npm ci for reproducibility. The security gate for new dependency adoption requires this committed candidate to pass blocking audit, then separate review of the proposed additions. Update 22 remains blocked by pinned SUMO installation, actual smoke scenario and topology validation. No dependency auto-install of SUMO or Three.js, no real-road actuation. Candidate delivery remains 21/39; accepted baseline unchanged.

### Opt-in SUMO runtime integration (0_5_67 candidate)

The existing CameraFrameService remains the sole authoritative simulator/camera owner and forwards committed virtual phase observations only to an opt-in ShadowRuntime. A bounded worker drives a separate libsumo child on local IPC; no native imports in the parent, no new network listener, no changes to physical camera or signal decision state. Default off (unset MESH_SUMO_SHADOW); controlled native and dependency CI gates passed on 22f; exact release commit CI and owner acceptance pending. Read-only synthetic diagnostics remain separate, with reset/stop/failure invalidation. Restricted generated four-arm geometry and east-west demand are not equivalent to the legacy cyclic single-crosswalk scene. No field or matched comparative performance evidence.


### Optional road renderer (S03; 0_5_68 candidate)

`SimulationCamera3D` retains camera controls, scene polling, source match and legacy overlay/editor plane. `ThreeRoadView` owns only WebGL lifecycle and viewport resize; `RoadRenderer` consumes immutable snapshots and canonical `roadGeometry.ts` reference pixels. Trial imports the same renderer. Opt-in, fallback on unsupported view/context failure; no simulator or signal authority. See [integration evidence](S03_RENDERER_INTEGRATION.md).

### Vehicle presentation motion (S03 / 24a)

Update 24a / S03 preparation: 0_5_68 release CI 45753611276 passed. Implement stable vehicle meshes by existing backend slot ID/signature; car/SUV/van/bus body, cabin, windows, lights, wheels; shared geometry and per-vehicle material cleanup. Pure time-based interpolation between authoritative snapshots only, bounded 450 ms, no extrapolation, source/density/reset/gap guards, immediate snap for recycled slots and pause/resume, mirrored heading. RequestAnimationFrame only while interpolating, cleanup on unmount; legacy editor/overlay fallback and APIs/controller untouched. Backend currently straight road; turning regression is synthetic, not live turning support. No new dependencies or physical outputs. New CI and screenshot pending; candidate remains 0_5_68.

#### 24b verification

Candidate `0_5_69`; previous `0_5_68`; accepted baseline `0_5_0`; Update 24 / S03. Owner PASS pending.

The opt-in Three.js preview uses distinct procedural car, SUV, van and bus meshes with body/cabin proportions, windows, wheels and lights. RoadRenderer retains mesh groups by backend vehicle slot ID and shape signature; removes absent groups and disposes owned materials. VehicleMotion interpolates authoritative observed centers and shortest-angle headings for at most 450 ms, without extrapolation or simulator-clock mutation. Large jumps, backwards straight movement, changed shape, source/density change, clock rollback or a gap over one simulation second reset the affected motion; pause/resume snaps to the authoritative pose. RequestAnimationFrame runs only during active interpolation. The legacy CSS renderer remains default and preserves editing/overlay fallback, camera coordinates and all backend APIs and signal authority. No dependency or physical output changes.

See [patch evidence](PATCH_0_5_69.md).

### Pedestrian presentation (S03 / 25a)

Update 25a / S03 preparation: exact 0_5_69 release CI 45754606972 passed. Persistent volumetric figures with head, torso, separate swinging limbs, shared box/sphere geometry and per-figure material disposal. Presentation follows observed positions only, distance-derived gait, bounded 450 ms interpolation, no extrapolation, no walking in place after stationary samples, pause/reset/source/density/large-gap/reentry guards, camera-mirrored heading and curb elevation. Existing backend phase and speed unchanged; fixed seeded tests call actual pedestrian movement helper for both directions, WALK entry, CLEAR continuation, non-WALK curb hold, slow fixture and reentry. No physical obstruction simulation or mobility classification claimed. Browser trial directly asserts persistent pedestrian group identity, interpolated pose, gait freeze and removal, preserves legacy fallback. No dependency, API, controller, hardware or coordinate editing changes. New CI and screenshot pending; version stays 0_5_69.

#### 25b verification

Candidate `0_5_70`; previous `0_5_69`; accepted baseline `0_5_0`; Update 25 / S03. Owner PASS pending.

The optional Three.js preview replaces pedestrian box proxies with persistent volumetric figures (head, torso, separate arms, legs, shoes). PedestrianMotion follows canonical observed positions, bounds interpolation to 450 ms, derives gait from observed displacement, stops gait when stationary/paused, and resets on backwards/large jumps, source/density/clock changes or gaps. RoadRenderer retains mesh groups by existing pedestrian slot ID and color; removes absent groups and disposes owned materials. Shared geometry, mirrored heading, curb elevation and existing animation scheduling are retained. No extrapolation, new crossing authorization, simulator speed or controller change. Legacy CSS remains default and retains the source-coordinate editor and overlays. No API, dependency or physical-output changes.

See [patch evidence](PATCH_0_5_70.md).

### Isolated lane scenario (0_5_71 candidate)

The trusted synthetic SUMO scenario is internally opt-in via `GeneratedSession(seed, lane_scenario=True)`; the standard shadow session and legacy authoritative simulator remain unchanged. The isolated libsumo worker uses the existing validated topology and protected phase upper bound. Seeded finite demand includes straight, left/right turns, a temporary downstream blocker and pedestrians. Lane-leader admission grants at most one vehicle link, rejects insufficient exit space, holds vehicle entry while a pedestrian or vehicle occupies the junction, and allows pedestrian entry only during pedestrian green with no vehicle inside. Yellow, flashing and all-red grant no new entry. No new network listener, frontend mode, API schema, dependency or physical output. Native SUMO retains lane following and motion ownership; the admission function is not an independent physical safety controller.

See [Patch 0_5_71](PATCH_0_5_71.md).

### Isolated two-junction corridor (0_5_72 candidate)

The optional `CorridorSession(seed)` generates a trusted two-junction SUMO fixture with centres 45 m apart and directed vehicle route WA → AB → BE. It reuses the pinned native child process, lane-leader exit-space admission and validated per-junction phase mapping. SUMO owns continuous vehicle motion and persistent IDs. `set_junction_phases` requires explicit virtual phases for both A and B; independently validated permissions, internal vehicle occupancy and pedestrian crossing occupancy restrict each junction. The downstream exit-space gate prevents upstream admission during observed spillback. No new dependency, saved topology integration, HTTP endpoint, frontend selection, physical output or live signal authority; standard shadow and legacy defaults remain unchanged.

See [Patch 0_5_72](PATCH_0_5_72.md).

### Native diagnostic frame publishing (Update 28 preparation)

The optional ShadowRuntime owns native observations from committed legacy phase steps. NativeProjection provides independent network geometry; NativeFramePublisher caches only one validated current-generation tick for diagnostic bundle and exact binary frame reads, with encoding outside the camera/worker condition lock and revalidation before publication. Scene-only reads avoid PNG work. Native IDs and explicit synthetic provenance never enter selected camera, saved sources, detector, editor or signal authority. Legacy remains authoritative; see [migration gates](SIMULATOR_MIGRATION_GATES.md).

### Common evaluation gate metrics (Update 28h preparation)

Isolated simulation_gate_metrics consumes normalized approach/service/exit observations. Engine adapters preserve native world and legacy pixel geometry; common event rules never feed controller, detector, editor or camera source. Existing experiment CSV semantics remain unchanged. See [migration gates](SIMULATOR_MIGRATION_GATES.md).

### Finite common service-gate evaluation (Update 28i preparation)

The isolated finite fixture parses the trusted generated network/route XML, supplies common physical vehicle and crossing paths and offered demand to a legacy-style reference and native route-aware measurement. Walking areas are reference chords, native dynamics are not reproduced, and the reference is not CameraFrameService. No selected camera, controller, detector, editor, persistence or physical outputs change.

### Standalone native evaluation milestone (Update 28 preparation)

An explicit startup flag enables a separate bounded native-only application service. Its manually stepped clock, temporary protected controller configuration, native child, route metrics, exact generation/tick publisher and capture archive belong solely to the evaluation instance. Native-only controls never select a saved camera, observe live traffic, or mutate production signal settings. Native Three.js uses actual lane polylines and observed positions, with SVG fallback; original editor pixels stay legacy. App shutdown retires the evaluation. No production authority switch.

### Native integration and acceptance batch

NativeProjection layout identity derives from lane geometry and projection parameters, not a legacy camera ID. Exact native view scenes return namespaced source identity and the independent coordinate space. Standalone playback is explicitly client-driven and bounded, serialized by the existing polling scope; exit/editor switch retires requests, and an already-issued single step may finish. The paired native experiment route copies the saved signal policy once and runs separate native fixed/adaptive sessions under the protected controller without modifying production configuration or experiment persistence. ZIP and view metadata distinguish native metrics and layout. Existing camera and region planes remain authoritative in production. See migration gates for limitations.

### Reconciled native workspace

Legacy experiment routes do not load native evaluation dependencies until the native endpoint is called. Simulation Lab exposes the same optional native service, with standalone A–D view selection and client playback, without changing selected camera. Region drafts use the existing native_projection_v1 layout identity, exact epoch/generation/tick and view, and never persist to production zones. Saved-policy comparison ZIP remains the sole paired native contract; matching demand digest and timeline checks plus derived native gate metrics/deltas augment it. Native permission readback must equal protected phase-map state. No production authority switch.

### S04 exact native observation and raster cache (unreleased)

The native evaluation publisher holds one immutable canonical raster and lazily validates/encodes each requested view, under its existing service lock. Existing shadow bundle publisher still validates all four external PNGs. Native region/world geometry, capture descriptor and scene share exact epoch/generation/tick/layout identity, with explicit non-authoritative synthetic ground truth; no selected camera, inference or live policy injection. Native demand manifests support independent finite-reference replay under identical requested phases; not production legacy movement or controller equivalence.

### S04 shared simulation publication and production metric bridge (unreleased)
Legacy frame owner caches one detached scene at raster publication and shares original source/frame identity with camera/AI consumers. Native and legacy use the same mirror convention and synthetic scene descriptor but explicitly distinct layouts. Density changes invalidate legacy observation lifetime; native is not registered with selected camera or inference services. Native shadow and standalone use one lazy publisher and release the raster once all four encoded frames exist. Native comparison reserves an isolated child, releases the parent lock for responsive status and closes/cancels at shutdown. Production benchmark can internally sample common normalized gates at 0.2 s without replacing original legacy metrics or live movement. Physical geometry/demand equivalence remains unproven.

### S04 shared exact read boundary (unreleased)
The common simulation observation route dispatches explicit legacy or native read owners and returns shared view-space centers/identity; exact frame reads require epoch/generation/tick/layout and never implicitly select or substitute another engine. Production multi-camera inference takes a single locked legacy publication across all requested saved simulation views. Native synthetic projections remain ineligible for the live detector cache even if misrouted internally. Native UI uses the common exact binary path; existing legacy/native routes retained. Geometry and demand equivalence, safe production engine interchangeability and owner acceptance remain gated.

### S04 shared legacy motion owner (unreleased)
Pure legacy_world module owns fixed pixel geometry, density counts/seed offsets, initial slot specs and deterministic movement/recirculation. Camera and isolated production benchmark retain their own locks, policy clocks, observation owners and metrics; both call the same movement functions. Opt-in live-slot benchmark initialization matches the camera, historical default unchanged. Native finite physical geometry remains explicitly different.

### S04 replaceable finite-session owner (unreleased)
NativeEvaluationService now selects GeneratedSession (SUMO) or GeneratedReferenceSession (finite constant-speed reference) through the same protected lifecycle. Both use trusted network and trip manifests, phase maps, GateMetrics, projection and exact publication. Reference has distinct provenance and source IDs, no libsumo child, and never becomes a live detector input. Engine switch retires the previous generation before reset. This is actual interchangeable evaluation execution, not a production geometry/demand migration; legacy_world remains production slot motion.

### S04 protected pixel-space migration bridge (unreleased)
CameraFrameService selects legacy or ProtectedCrosswalk at explicit paused reset; both reuse legacy_world movement, camera raster, clock, region plane and inference transport. Protected checks opposing committed occupancy before and after each step, tracks slot reentry visits, fixes backwards stop-line movement without changing the historical legacy rule, and fails closed. Actual selected simulation camera is still synthetic; isolated SUMO/reference evaluation stays separate. Protected is not a metre-calibrated SUMO engine.

### S04 production experiment integration (unreleased)
ProtectedCrosswalk owns both camera and experiment motion/admission, with optional measurement callbacks invoked in the shared movement path. Protected slots use deterministic per-agent random streams; legacy default and historical shared RNG unchanged. Simulation Lab exposes the protected model and exact requested/applied phase evidence. The native frame publisher can take ownership of the renderer's fresh exclusive raster, retaining default defensive copies for other callers and exact PNG pixel verification. This removes one 2.64 MiB transient raster copy, not the native child working-set cost.

### S04 native cyclic midblock lifecycle (unreleased)
CyclicMidblockSession reuses LibsumoSession private process transport and SumoShadowAdapter lifecycle under NativeEvaluationService. Trusted generated explicit lane-separated road and footpath topology, strict phase-map readback, single-crossing route validation, committed occupancy with conservative longest-vehicle tail clearance and actual arrived-ID accounting. Separate stable slot identity and unique journey ID; parent independently reconciles child reoffers and refuses arrival without observed gate. No teleport or forced insertion. Existing finite sessions unaffected. Native publisher retires stale raster/frame cache on clock advance while retaining a minimum tick guard, removing retained image memory during scene-only periods. This is an opt-in native migration candidate, not a replacement default or calibrated legacy coordinate plane.

### S04 midblock route correction and footprint publication (unreleased)
Retained netconvert topology confirmed correct two vehicle / one pedestrian conflict partition but disconnected reverse approach. Keep exact topology, traverse the connected bidirectional pedestrian route in reverse with explicit start/end positions. Native child and parent independently qualify admission, observed progress and exits; no gate skip, collision, teleport or unobserved arrival can reoffer a slot. The projection owns slot/visit/type/physical dimensions consistently for scene and PNG raster. Native 3D places the physically scaled vehicle body behind the observed front centre, with heading determined by the declared straight route. Existing finite fixture projections unchanged. No production inference enablement or legacy region remapping.

### S04 native camera workspace and exact coordinate pipeline (unreleased)
The production camera page now exposes a separate native evaluation camera preview directly, including four views, midblock playback, capture, comparison and draft evaluation, without requiring the legacy simulator to run. No camera profile, stream or detector authority changes. The nested legacy preview retires its redundant polling while native display is active; scoped polling rejects retired results. Native PNG fetch validates exact frame response headers and revokes browser blob URLs when tick/view/generation retires. Shared native region draft service evaluates all four mirrored planes on one immutable native snapshot and rejects disagreement. Native walking-area shape polygons are filled in raster/SVG and triangulated in WebGL rather than stroked; degenerate terminal polygons are not enlarged, and mesh geometry is disposed on generation reset. The legacy/finite rendering contract remains unchanged. Resource gate is still unresolved; no causal latency/RSS reduction claim until repeat measurement.

### S04 bounded native preview ownership and indexed raster (unreleased)
The camera workspace owns its isolated native session through a generation-qualified lease rather than borrowing mutable standalone state. Timer expiry/release uses the existing serialized retirement path (adapter shutdown/reap, cache invalidation, generation advance); ordinary readers do not renew it, only matching owner commands/heartbeat. A lease timer is armed once at start and rescheduled to remaining deadline when renewed, cancelled on retirement. No background traffic stepping. UI blocks mutations of another workspace's session, releases on unmount and renews while mounted; disconnection cannot keep an orphan child indefinitely (subject to current bounded child operation and reaping). Native evaluation remains separate from selected production camera and AI. Midblock projection directly draws palette indices using shared shape/drawing code: canonical background and current raster each 921600 bytes versus 2764800 RGB; at most one background and one publication raster retained. Standard-library PNG chunks/CRC/DEFLATE, no quantisation or additional dependency. Independent OpenCV BGR decode and per-channel LUT comparison still required before any frame published; failure invalidates all views. Matched RGB control uses same rendering and runtime via constructor-only switch (not public setting). Existing RGB path unchanged. No claim of whole-process memory parity or native detector compatibility.
