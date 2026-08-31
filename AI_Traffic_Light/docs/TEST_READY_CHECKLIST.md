# V0311 Acceptance Checklist

- [ ] `VERSION` is `0_3_11`; previous is `0_3_10`; passed baseline remains `0_2_4`.
- [ ] `docs/PATCH_0_3_11.md`, `CHANGELOG.md`, and the shared frontend `PROJECT_VERSION` all identify the same V0311 candidate.
- [ ] The normal Windows command remains reusable:

  ```powershell
  & "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
  ```

- [ ] The normal full workflow passes Python compile, structure validation, all automatic backend regressions, frontend typecheck/build, Git cleanliness and live backend smoke.
- [ ] `scripts/test_intersection_network.py` passes with V0311 layout/primary-source/backward-schema assertions.
- [ ] `scripts/test_junction_network_overview.py` passes.
- [ ] `GET /api/traffic/network/overview` returns through the standard success envelope and request-ID middleware.
- [ ] Junction Network appears under the Traffic navigation section and loads without a frontend fallback/type error.
- [ ] Existing schema-1 `config/intersections.json` files without `position` or `primary_source_id` load with deterministic defaults.
- [ ] Junction node positions persist after Save and PC Studio restart.
- [ ] Directed topology lines persist after Save and display between their configured source/destination junctions.
- [ ] One junction can be assigned two or more saved ESP cameras.
- [ ] One camera/source id cannot remain assigned to two junctions at the same time; reassignment is explicit.
- [ ] `primary_source_id` is either null or one of that junction's assigned `source_ids`.
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
