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
