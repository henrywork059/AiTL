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
