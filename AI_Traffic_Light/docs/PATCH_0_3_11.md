# Patch 0_3_11 — Junction Network visualization

V0311 / `0_3_11` is the current unaccepted candidate after V0310. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Purpose

V0311 adds one PC Studio workspace for representing installed/model AiTL junctions as nodes and directed topology lines, assigning saved ESP cameras to those junctions, and exposing the current prototype traffic/pedestrian/event/warning context without overstating the existing inference architecture.

## Implemented

- Reuses the established `config/intersections.json` network configuration rather than creating a parallel junction database.
- Extends each intersection with a persisted canvas `position` and optional `primary_source_id` while retaining schema version 1 compatibility.
- One junction may own several `source_ids` / ESP cameras.
- One source id may belong to only one junction, preserving unambiguous live source-to-junction identity.
- Older schema-1 intersection files without V0311 layout/primary-source fields receive deterministic defaults when loaded/saved.
- Adds `GET /api/traffic/network/overview` using the standard API envelope/request ID path.
- The overview projects configured junctions/links, saved ESP camera state, selected/current source identity, vehicle and pedestrian load, current phase/decision, ranked-scenario/service/manual-test events, and camera/source warnings.
- Adds the PC Studio **Junction Network** page under the Traffic section.
- Junction nodes can be added, removed, renamed, enabled/disabled, dragged and persisted.
- Existing network links are visualized as directed lines; outgoing links can be added, removed, enabled/disabled and given a travel-time value.
- Saved ESP cameras can be assigned/reassigned from the page. Multiple cameras can be assigned to one junction and one assigned source can be marked primary.
- Node badges show vehicle load, pedestrian load, camera count, phase, event count and warning count.
- The detail panel exposes current live state, camera health/FPS, topology links, events and warnings.

## Live-data boundary

V0311 does **not** create a separate detector/controller pipeline for every junction. PC Studio still has several independent ESP stream workers but exactly one selected physical/simulation source feeds the shared inference/traffic pipeline.

Therefore:

- the junction resolved from the current selected frame/source may show current AI/simulation traffic metrics;
- other junctions show topology and camera-health information but their occupancy/load is explicitly unavailable;
- a configured link does not imply observed vehicle transfer or active cooperative signal control;
- camera assignment does not imply cross-camera identity/fusion;
- all traffic phases remain prototype simulation/recommendation/display outputs only.

## Deliberate non-changes

- V0310 ESP production camera transport remains unchanged.
- No GIS/geographic map is added; this is an editable logical topology canvas.
- No simultaneous multi-camera inference fusion is added.
- No automatic cross-camera tracking/identity matching is added.
- No public-road/cabinet signal control is added.
- Existing network simulation/cooperation/emergency/class/pedestrian experiment semantics remain unchanged.

## Validation focus

The automatic local workflow should verify:

1. project structure/version consistency;
2. existing intersection-network regression plus V0311 primary-source/layout validation;
3. V0311 overview-service regression for multi-camera assignment, camera health, live source mapping, event/warning projection and unavailable non-selected junctions;
4. backend/API regressions;
5. frontend TypeScript typecheck and production build;
6. live backend smoke sequence and normal PC Studio startup.

## Owner acceptance checks

After the normal one-command update/test/run workflow passes:

1. Open **Traffic → Junction Network**.
2. Confirm the page loads the existing default/configured junction network.
3. Add at least two junctions and drag them to different positions.
4. Add at least one directed line between junctions and save.
5. Assign two saved ESP cameras to one junction and, if another junction owns one of them, confirm the explicit reassignment prompt.
6. Select one assigned camera as the primary source and save.
7. Reload/restart PC Studio and verify junction positions, links and camera assignments persist.
8. With one ESP selected/streaming, verify that its resolved junction can display live traffic/pedestrian information while another unselected junction remains clearly unavailable rather than showing copied/fabricated counts.
9. Disconnect or make an assigned ESP unavailable and verify a camera warning is visible.
10. Trigger an existing simulation/test ranked scenario or pedestrian service and verify the selected observation junction displays the corresponding event badge/detail.
11. Verify Camera Sources, Live AI, Camera Diagnostics, zones, analytics, dataset and simulation pages still operate normally.
12. Do not change `passed_baseline` until the owner explicitly accepts V0311.

AiTL remains a local/student-scale prototype with no physical/public-road traffic-signal authority.
