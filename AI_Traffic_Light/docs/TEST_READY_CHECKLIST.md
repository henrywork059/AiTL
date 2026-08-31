# V0311 Acceptance Checklist

- [ ] `VERSION` is `0_3_11`; previous is `0_3_10`; passed baseline remains `0_2_4`.
- [ ] `docs/PATCH_0_3_11.md`, `CHANGELOG.md`, `START_HERE.md`, `LOCAL_TESTING.md`, this checklist, and the shared frontend `PROJECT_VERSION` identify the same V0311 candidate/baseline state.
- [ ] The normal Windows command remains reusable:

  ```powershell
  & "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
  ```

- [ ] Cheap Python compile / structure / release-document / runner self-checks execute before dependency installation.
- [ ] With no backend/frontend dependency-manifest changes, a repeated normal run skips redundant `pip install` / `npm ci` while still running regressions, frontend typecheck/build, Git cleanliness, live smoke and startup.
- [ ] `-RefreshDependencies` forces backend/frontend dependency refresh when explicitly requested.
- [ ] The normal full workflow passes all automatic backend regressions, frontend typecheck/build, Git cleanliness and live backend smoke.
- [ ] `scripts/test_release_documentation_consistency.py` passes and verifies current/previous/baseline documentation alignment, frontend version, patch-playbook safeguards and current production architecture markers.
- [ ] `scripts/test_update_test_run_script.py` passes including preflight ordering, dependency-diff optimization, automatic zero-argument `test_*.py` discovery and hardware-only test separation.
- [ ] `docs/PATCH_PLAYBOOK.md` exists and documents the short preflight, implementation order, **release bundle then VERSION last**, automatic regression naming, code-review gate, dependency-aware runner and one-command owner validation.
- [ ] `scripts/check_structure.py` requires the Junction Network/playbook/current-document surfaces, checks intersection config atomic persistence and guards serial Junction Network polling.
- [ ] Durable `ARCHITECTURE.md` describes the V0310 production camera path as one framebuffer + `CAMERA_GRAB_LATEST`, not the obsolete two-framebuffer production description.
- [ ] Durable `CODE_STRUCTURE.md` identifies `intersection_network.py` as topology/config owner and `junction_network_overview.py` as a read-only projection.
- [ ] `scripts/test_intersection_network.py` passes with V0311 layout/primary-source/backward-schema assertions.
- [ ] Explicit `primary_source_id: null` persists as null after save/reload even when the junction has assigned sources.
- [ ] A legacy schema-1 junction that omits `primary_source_id` still receives the first assigned source as the migration default.
- [ ] `scripts/test_junction_network_overview.py` passes.
- [ ] `scripts/test_junction_network_frontend_structure.py` passes including navigation, App routing and central function-registry checks.
- [ ] `GET /api/traffic/network/overview` returns through the standard success envelope and request-ID middleware.
- [ ] Junction Network appears under the Traffic navigation section and loads without a frontend fallback/type error.
- [ ] Junction Network capabilities appear in the central frontend function registry/status catalog.
- [ ] Existing schema-1 `config/intersections.json` files without `position` load with deterministic defaults.
- [ ] Junction node positions persist after Save and PC Studio restart.
- [ ] Directed topology lines persist after Save and display between their configured source/destination junctions.
- [ ] One junction can be assigned two or more saved ESP cameras.
- [ ] One camera/source id cannot remain assigned to two junctions at the same time; reassignment is explicit.
- [ ] `primary_source_id` is either null or one of that junction's assigned `source_ids`.
- [ ] Setting **Primary camera → None** in Junction Network survives Save + PC Studio restart.
- [ ] Camera rows show saved ESP identity, host/state and measured FPS when available.
- [ ] Current vehicle/pedestrian load, phase and decision appear only on the junction resolved from the shared selected camera/simulation source.
- [ ] At least one other unselected junction displays unavailable traffic load instead of copied/fabricated counts.
- [ ] Ranked scenario, pedestrian-service or manual/test events display on the current observation junction when triggered with their existing provenance.
- [ ] An unavailable/erroring assigned ESP produces a visible warning.
- [ ] A junction with no assigned source produces an informative no-source warning.
- [ ] Existing Camera Sources multi-camera management still works; V0311 does not create or claim simultaneous multi-junction inference.
- [ ] Existing network topology remains configuration metadata; the new page does not imply observed transfer or activate cooperative signal control.
- [ ] V0310 production camera transport and its Arduino sketch remain unchanged by V0311.
- [ ] Camera Sources, Live AI, Camera Diagnostics, Zone Editor, Traffic Logic, Traffic Analytics, Simulation Lab, Dataset, Training and Models remain usable.
- [ ] No new stable error code is required; existing traffic-network validation/read/write errors remain authoritative.
- [ ] No physical/public-road traffic-control authority is introduced.
- [ ] Owner explicitly accepts V0311 before `passed_baseline` changes.
