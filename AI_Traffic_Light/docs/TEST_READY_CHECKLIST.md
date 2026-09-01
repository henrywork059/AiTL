# V0311 Passed Record

Owner acceptance date: 2026-09-01

Release state:

```text
version: 0_3_11
previous_version: 0_3_10
passed_baseline: 0_3_11
status: owner-confirmed passed baseline
```

The owner explicitly confirmed that V0311 is running correctly and passes. The following acceptance items are recorded as satisfied for the passed baseline:

- [x] Normal reusable Windows command updates, validates and launches PC Studio.
- [x] Python compile / structure / release-document / runner self-check path is in place.
- [x] Dependency-aware repeated runs may skip redundant `pip install` / `npm ci` while retaining regressions/typecheck/build/smoke.
- [x] `-RefreshDependencies` remains available for an intentional forced dependency refresh.
- [x] Automatic zero-argument `scripts/test_*.py` discovery is preserved; hardware-only utilities remain separated.
- [x] `docs/PATCH_PLAYBOOK.md` defines the short preflight, implementation order, release-bundle-before-VERSION rule, regression convention and handoff flow.
- [x] Durable camera architecture documents FB1 + `CAMERA_GRAB_LATEST` rather than the obsolete two-framebuffer production claim.
- [x] Junction Network is wired into Traffic navigation, App routing and the central function registry.
- [x] Junction node positions and directed topology lines persist.
- [x] One junction can own multiple saved ESP cameras.
- [x] One camera/source ID cannot remain assigned to two junctions simultaneously.
- [x] `primary_source_id` is nullable or one of the junction's assigned sources.
- [x] Explicit **Primary camera → None** persists as null; legacy omitted primary-source metadata still gets the migration default.
- [x] Camera health/FPS and warning state are available to Junction Network.
- [x] Current vehicle/pedestrian load, phase and decision are shown only on the junction resolved from the selected shared source.
- [x] Non-selected/unobserved junctions show unavailable live load instead of copied/fabricated counts.
- [x] Ranked-scenario/pedestrian-service/manual-test events retain existing provenance semantics.
- [x] Existing Camera Sources multi-camera management remains compatible.
- [x] V0310 production camera transport/Arduino sketch remains the active ESP production path.
- [x] No simultaneous multi-junction inference is claimed.
- [x] No physical/public-road signal-control authority is introduced.

Future development should treat `0_3_11` as the known-good baseline. A future patch increments `Z` only when the owner explicitly requests the next patch/version.
