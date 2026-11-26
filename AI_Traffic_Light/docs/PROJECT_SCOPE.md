# Project Scope

## V0553 read-only endurance recorder

The standalone `scripts/camera_endurance_benchmark.py` polls the already-exposed multi-camera status API and exports per-source CSV samples and a JSON summary, including saved capture settings, receiver frame age/FPS, sequence diagnostics and observed reconnection timing. It does not initiate or control ESP streams, decode captured image payloads, infer traffic behavior or actuate any signal. Optional process CPU/memory requires an explicitly identified backend PID and optional psutil. Status-poll and synthetic fixture evidence are not equivalent to a validated hardware endurance run. Only individually keyed `cameras[]` observations are consumed; the existing selected-status concurrency race is not repaired by this benchmark.

## V0554 device contract foundation

A versioned, read-only per-camera capability/health descriptor is projected from the existing saved camera manager. It reports supported PC camera input and simulation-only input separately from current availability, and marks lighting/speaker outputs unavailable. The descriptor is not a hardware module registry, discovery system, authenticated module protocol, physical output interface or safety certification. Existing saved profiles remain V1; no new persistence or device command is introduced.

## V0555 setup and connection workflow

The existing saved-camera setup UI validates private-LAN input and settings, reports source-specific connection errors and retry guidance, and distinguishes transport connectivity from fresh image availability. Failed Connect retains the saved profile; explicit retry does not start the stream. The manager status refresh preserves selection identity across asynchronous device probes. No new output or physical actuation capability.

## V0556 fake-only bench abstraction

Only a synthetic demo indicator is supported by an isolated, disabled-by-default in-memory adapter. Tests exercise bounded command leases, acknowledgment faults, explicit off, disconnect and monotonic expiry. Physical lighting, speakers, traffic signals and other real outputs remain unavailable; no hardware authorization, real electrical testing or physical watchdog is implied.

## V0557 synthetic lighting preparation

The isolated `FakeLightingDemo` delegates binary synthetic pulses to the existing fake bench controller (integer duration 1–2000 ms, acknowledgment bound 100 ms). It is disabled by default, requires explicit test arming, and fails closed on invalid/overlapping requests, acknowledgment faults, disconnect, expiry and generation changes. Status is explicitly simulation-only and physical lighting remains unavailable. No live route, UI, GPIO, network or firmware integration. Physical integration is BLOCKED: lighting model, voltage/current requirements, driver/electrical interface and controlled-bench authorization remain unconfirmed; an independent hardware fail-safe is not implemented. No physical testing or electrical safety validation was performed.

## V0558 synthetic speaker preparation

The isolated `FakeSpeakerDemo` reuses the existing fake bench controller for a metadata-only demonstration of two predefined notices (`demo_attention`, `demo_accessibility`). Integer normalized volume 1–100% and duration 1–2000 ms are synthetic test bounds, not acoustic levels or certified limits. Explicit test arming is required; invalid or overlapping commands, acknowledgment faults, off, disconnect, generation changes and expiry clear the active notice. No audio playback, arbitrary speech, live route, UI, GPIO, network or firmware integration. Physical speaker integration is BLOCKED: hardware model, amplifier/driver, electrical specifications, acoustic limits, independent hardware fail-safe and controlled-bench authorization remain unconfirmed or unavailable. No acoustic or physical safety validation was performed. Physical lighting also remains blocked.

## Physical camera input

AiTL implements a local PC-controlled ESP32-CAM input path with:

- idle Connect/status probing with zero image transfer;
- PC-owned OV2640 runtime configuration;
- persistent low-latency length-prefixed TCP JPEG image transport;
- quality-preserving V037/R6 behavior that keeps configured JPEG quality and resolution fixed across transport pressure;
- V0310 production tuning that uses one framebuffer, `CAMERA_GRAB_LATEST` on PSRAM, and bounded plain TCP sends while retaining the existing ATL1 wire/session contract;
- transport/session recovery after temporary network or ESP restart;
- a persistent list of saved ESP private-LAN IP addresses and per-camera settings;
- several independent ESP stream workers/newest-frame caches that may run concurrently;
- explicit user selection of exactly one ESP for the legacy selected-source dataset capture, zones/tracking and analytics pipeline; V059 adds one shared background model serving independent latest frames from saved cameras for Camera AI Preview;
- a V038 one-click diagnostic workflow that isolates control reachability, firmware/camera readiness, Wi-Fi margin, direct camera TCP transport, control/stream contention, and the normal PC Studio managed receiver path.

Source switching is freshness-guarded: the previous selected physical frame is cleared during a switch, a cached frame is promoted only when it is recent, and replaced device sessions are generation-guarded so late old-IP frames are rejected. This prevents an old or wrong-source image from being presented as a new active AI input.

Camera diagnostics are local prototype evidence. A run may temporarily quiesce the selected stream/simulation, measure the selected camera using its saved image settings at a conservative target FPS, and restore the prior state. A diagnostic label identifies the most likely failing layer; it is not a certification of network, detector, or camera reliability.

## Network — crossing graph and junction compatibility

The Network page now prioritizes all saved crosswalks as automatically created crossing boxes, with camera connection health and current-source-only region observations. Users can arrange them and connect numbered edges as persisted logical topology. This does not establish measured vehicle transfers, multi-camera identity matching or cooperative signal control. Camera AI Preview independently infers available cameras in V059. Existing junction configuration remains available as an advanced section.

### Retained junction installation / topology view

V0311 implements a logical Junction Network workspace over the existing intersection-network configuration.

Implemented scope includes:

- persistent junction identity, label, enabled state, signal-profile metadata and logical canvas position;
- directed topology links with approach/travel-time metadata;
- assignment of multiple source/camera ids to one junction;
- one optional primary source per junction;
- exclusive source ownership across junctions so a live source maps to one junction only;
- saved ESP camera health/reachability/streaming/FPS observability per assigned junction;
- live vehicle/pedestrian load, phase/decision, event and warning projection for the junction resolved from the shared selected source;
- explicit unavailable state for junctions that do not currently own the shared observation.

The Junction Network canvas is logical topology, not GIS/geographic positioning. Configured lines represent topology metadata; they do not prove observed traffic transfer or activate cooperative signal control.

## Current capability boundary

This does not imply:

- ESP-side inference;
- validated production detector accuracy;
- independent per-camera traffic-controller pipelines for all connected cameras/junctions (one background model provides independent camera preview detections only);
- multi-camera image fusion at one junction;
- automatic cross-camera object identity/transfer matching;
- live emergency-vehicle recognition/pre-emption;
- physical/public-road traffic-signal authority.

Existing cooperation, pedestrian, class, emergency and explainability/evidence features retain their documented prototype/simulation provenance. Multiple physical camera inputs plus V0311 camera-to-junction assignments are a stronger data/configuration foundation for later multi-intersection work; they do not by themselves activate live cooperative control.

## V059 AI Models and Camera AI Preview

AI Models uploads/activates/deletes local YOLO .pt files, blocks deletion of the running model, and persists global confidence and target inference interval. A single background inference worker samples the freshest frame from each saved streaming ESP or saved simulation camera, with per-camera detection results and no queued backlog. Camera AI Preview lets users switch among registered cameras, displays labeled boxes and side-specific crossing regions, and counts current per-class observations outside the frame. These are **preview-only detections**; not calibrated cross-camera uniqueness, fused occupancy, autonomous network control or reliable on-road signal actuation. The Settings UI is removed without removing the existing backend settings API.

## V0510 bounded signal adjustment prototype

Implemented: editing active-profile default signal durations; disabled-by-default live-adjustment scenario presets; slow clearance near-end metric; read-only current simulator signal/adjustment display on a source-matched Network crosswalk; advisory notification to linked neighbours. Rule execution requires supported current observed detector/zone data and follows the existing safe transition sequence.

Not implemented: independent signal controller per crosswalk, conflict movement definitions and validated adjacent phase arbitration, cross-camera observation fusion into each crossing's controller, hardware emergency priority/identity validation, public-road commands or flashing green. Connected Network edges alone do not authorize signal changes.

## V0512 source-to-crosswalk observation routing

Implemented foundation: automatic fresh per-camera AI inference mapping into saved physical Crosswalk regions and their independent simulated signal-controller class condition observations, including Side A/B per-class average where synchronized and explicit partial/unavailable status. Region classes must be supported by the active model. A generic polygon does not establish pedestrians waiting, slow-moving, or vehicle queue semantics; those signals remain unavailable to crosswalk controllers until roles/tracking are configured. Signal output remains simulation only, and connected Network links do not coordinate phases or actuate physical lights.

Real ESP camera detections can now feed the same independent controllers as explicitly labeled **virtual software previews** without switching on camera simulation. This is not an observed/actuated physical traffic light; virtual previews expire if source frames become invalid.

## V0514 virtual Network conflict coordination

Simulation/virtual preview only: Users can define vehicle/pedestrian conflict pairs per connected Crosswalk link; independent controller outputs are supervised so conflicting published green permissions are suppressed. Blocked virtual phase clocks pause and resume after a minimum clearance gap. Emergency vehicle requests are one-hop, explicitly enabled, bounded and subject to the interlock. Camera inference and Side A/B region counts stay assigned per Crosswalk. No physical signal authority, independent conflict geometry verification, proven emergency detection or certified cross-junction safety is claimed.


### Observation identity foundation (0_5_59 candidate)

Internal camera identity is shared by synthetic and ESP producers. External upload provenance is not verified physical evidence. No additional perception, multi-junction fusion, control authority or hardware validation is implied.


### Tracking isolation foundation (0_5_61 candidate)

Selected-source tracking resets on camera/junction or acquisition scope changes; bounded replay guards prevent repeated cached observations from creating new tracks while retained. No concurrent multi-camera tracking, cross-camera identity matching or independently aggregated junction flow is established.


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


### Three.js road preview (Update 23 / S03; 0_5_68 candidate)

Optional read-only synthetic preview; CSS remains default and mandatory for editor/overlays. Shared scene polling, controls and protected virtual signals unchanged. Coarse agents; no calibrated projection, physical control, comparative GPU performance or owner acceptance. See [integration evidence and gates](S03_RENDERER_INTEGRATION.md).
