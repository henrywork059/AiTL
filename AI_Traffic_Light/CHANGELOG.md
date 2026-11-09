Warning: truncated output (original token count: 29086)
Total output lines: 944

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

- Standardize responsive typography and wrapping in existing shared `styles/base.css`, `styles/layout.css` and `styles/components.css`: fluid headings/metric figures, text…19086 tokens truncated…sistent user-configurable simulation policy while preserving the protected phase order.
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
