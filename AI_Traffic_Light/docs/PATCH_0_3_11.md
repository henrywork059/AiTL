# Patch 0_3_11 — Junction Network visualization

V0311 / `0_3_11` is the current owner-confirmed passed baseline as of 2026-09-01. V0310 / `0_3_10` is the previous candidate.

## Purpose

V0311 adds a PC Studio Junction Network workspace for representing installed/model AiTL junctions as nodes and directed topology lines, assigning saved ESP cameras to those junctions, and exposing current prototype traffic/pedestrian/event/warning context without overstating the existing inference architecture.

The same version also includes workflow/code hardening so future development uses a shorter preflight, automatic focused-regression discovery, safer release-metadata ordering, faster repeated validation and fewer stale architecture/version claims.

## Implemented

- Reuses `config/intersections.json` instead of creating a parallel junction database.
- Persists junction canvas `position` and optional `primary_source_id` with schema-1 backward compatibility.
- One junction may own multiple camera/source IDs; one source remains exclusive to one junction.
- Explicit `primary_source_id: null` persists as null; legacy records that omit the field receive the first assigned source as a migration default.
- Adds `GET /api/traffic/network/overview` through the standard API envelope/request-ID path.
- Projects configured nodes/links, saved ESP camera health, selected/current source identity, vehicle/pedestrian load, phase/decision, events and warnings.
- Adds **Traffic → Junction Network** with draggable nodes, directed links, add/remove/edit, camera assignment/reassignment, primary-camera selection, load badges, events and warnings.
- Registers Junction Network topology, camera assignment and observability in the frontend function registry.

## Live-data boundary

V0311 does **not** create a detector/controller pipeline for every junction. Several ESP stream workers may exist, but exactly one selected physical/simulation source feeds the shared inference/traffic pipeline.

Therefore:

- only the junction resolved from the selected frame/source may show current AI/simulation traffic metrics;
- other junctions show topology/camera health but live occupancy/load is explicitly unavailable;
- configured links do not imply observed vehicle transfer or active cooperative signal control;
- camera assignment does not imply cross-camera identity/fusion;
- all traffic phases remain prototype simulation/recommendation/display outputs only.

## Workflow hardening included in V0311

- Added `docs/PATCH_PLAYBOOK.md` as the short future patch path.
- Durable architecture now matches the V0310 production camera path: FB1 + `CAMERA_GRAB_LATEST`.
- New-candidate guidance uses **release bundle first, root `VERSION` last**.
- Ordinary zero-argument `scripts/test_*.py` regressions are auto-discovered by the normal runner.
- `check_structure.py` and `test_release_documentation_consistency.py` catch release/document/architecture drift earlier.
- `test_update_test_run_script.py` protects runner behavior, automatic test discovery and hardware-test separation.
- The normal Windows runner is dependency-aware: unchanged dependency manifests skip redundant `pip install` / `npm ci`, while full regressions/typecheck/build/smoke still run.
- `-RefreshDependencies` remains the explicit recovery path when dependency refresh is intentionally required.

## Production camera path

V0311 does not change ESP firmware. Continue using the V0310 production sketch:

```text
apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino
```

## Owner acceptance

On 2026-09-01 the owner explicitly confirmed that V0311 is running correctly and passes. Root `VERSION` therefore records `passed_baseline: 0_3_11`.

The acceptance covers the V0311 Junction Network behavior and same-candidate hardening present on `main` at acceptance time. Future normal patch development starts from `0_3_11`; increment `Z` only when the owner explicitly requests the next patch/version.

AiTL remains a local/student-scale prototype with no physical/public-road traffic-signal authority.
