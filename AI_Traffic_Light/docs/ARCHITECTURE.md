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
