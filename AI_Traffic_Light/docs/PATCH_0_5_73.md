# V0573 — Independent P4 hardware-first workspace candidate

Candidate `0_5_73`; previous `0_5_72`; accepted baseline `0_5_0`. Update 29 / U01 delivered as candidate; Updates 30–31 / U02 and 33 / U02 partial. Owner PASS pending.

## Implementation

Six navigation groups (Overview, Devices, Network, Simulation, AI Lab, Analytics); all 16 nonlegacy destinations preserved, simulation workspace opt-in. Shared desktop/mobile shell with API/source-mode/version context, skip link and responsive picker. Camera workflow retains transport/profile handlers; device form and diagnostics layout simplified, empty-state media text corrected. Dashboard distinguishes unavailable validation and source status. Crossing inspector selection reveals the selected node, existing keyboard/pointer connections and persisted coordinates retained. Model registry uses strict reads, searchable active/default-prioritized model list, refresh/error handling and responsive upload/settings. Existing backend routes, data formats, model files, camera transport, protected signal decisions and physical restrictions retained. No new dependencies or production backend changes in the independent P4 batch.

## Verified evidence

Application revision `58b88d4f119347fa8abfaabc592dff10dfaae781`: [standard CI 46008844336](https://github.com/henrywork059/AiTL/actions/runs/46008844336) passed all steps, including 126 discovered offline regression scripts, frontend data-access tests, typecheck, build and blocking npm audit. [Browser CI 46008844185](https://github.com/henrywork059/AiTL/actions/runs/46008844185) passed workspace, renderer and integration trials. Actual headless Windows browser renders of production components with synthetic API fixtures; not field evidence. [Artifact 15203510241](https://github.com/henrywork059/AiTL/actions/runs/46008844185/artifacts/15203510241) SHA-256 `3f88d3f71ef4c2c169eab84d2c2c34226e7e9727440ebe94a742f123b91fac41` independently matched. Corrected camera screenshot inspected: high-contrast empty preview, selected camera B connected but no received frame, stopped stream and camera A unchanged. Corrected network screenshot inspected: one saved link, selected crossing visible, inspector endpoints North [2] / South [4], no verified signal, no assigned cameras. Browser assertions cover camera selection, failed probe/profile retention, retry/start/stop, unverified-frame rejection, other-camera isolation, keyboard link creation/save/visible retention/API reload, model filtering/load/error/recovery, missing validation and responsive navigation/overflow. Exact release commit standard CI pending at publication. Prior native CI 45996915921 passed separately; not an S04 migration acceptance.

## Owner acceptance

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify version 0_5_73 Candidate, all navigation destinations and simulation toggle, narrow-window navigation and keyboard focus, unavailable dashboard states, saved camera selection/connect/retry/start/stop with authorized local bench only, no stale preview, crossing link save/reload and no conflicting signal authority, AI model filter/load/error/recovery using trusted local weights only. Check saved regions and dataset preservation. Verify legacy simulator default and optional renderer/editor fallback. Owner alone confirms PASS; no public-road outputs.

## Limitations and next steps

Update 29 / U01 delivered as a software candidate (navigation inventory, narrow/desktop browser and existing route/keyboard controls); 28/39 numbered milestones delivered as candidates (71.8%), not owner accepted. Updates 30, 31 and 33 remain partial: owner live Windows camera/editor and simulation-mode checks; comprehensive topology edit/delete, source assignment and stale observation workflow; capture/review/edit/export and training workflow acceptance, respectively. Network fixture proves UI/request/reload behavior; offline backend tests separately prove persistence and invalid-link rejection. Browser model activation uses mock API responses, not actual YOLO inference. Existing scrollable map can clip other nodes while selected node remains visible. Preserve existing light/dark tokens; no further optional restyling. S04/Update 28 remains open: legacy-compatible metrics, production coordinate calibration, trusted detector evidence, owner-PC matched resource/latency budget and acceptance, rollback and migration gates in [SIMULATOR_MIGRATION_GATES.md](SIMULATOR_MIGRATION_GATES.md). Updates 32/34 remain gated. No public-road signal actuation or accepted baseline change.

