# Changelog
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

- Created V026 / `0_2_6` at the owner's explicit request while V025 remained unaccepted; `previous_version` is `0_2_5` and the owner-confirmed `passed_baseline` remains V024 / `0_2_4`.
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
- Physical public-road traffic control remains disabled.
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
- Still intentionally excludes real YOLO inference, real camera capture, training, model export, and physical traffic-light control.
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
