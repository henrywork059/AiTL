# Human Guide

This guide is for the project owner, students, teachers, and reviewers using **AI Traffic Light (AiTL)**. It is intentionally version-agnostic; read root `VERSION` and `START_HERE.md` for the current candidate.

## 1. What AiTL is

AiTL is a local prototype for studying computer vision and adaptive traffic-light **simulation**.

```text
camera or synthetic scene
→ local object detection
→ zones/tracking/counting
→ simulated signal scenario evaluation
→ explanation, analytics, experiments and junction visualization in PC Studio
```

It also contains a local dataset/training workflow, multiple saved ESP camera inputs, an editable Junction Network view, and simulation/evidence foundations for multi-intersection work.

AiTL is **not** a certified public-road traffic-control system and does not connect its simulated decisions to public traffic infrastructure.

## 2. Where to start

For current project state:

1. Read `../VERSION`.
2. Read `START_HERE.md`.
3. Read `PROJECT_SCOPE.md` to distinguish implemented, foundation, simulation-only and planned capabilities.
4. Use `LOCAL_TESTING.md` / `TEST_READY_CHECKLIST.md` when testing the current candidate.
5. Use `DOCUMENTATION_MAP.md` if documents appear to disagree.
6. Use `PATCH_PLAYBOOK.md` for the shortest future-development workflow.

## 3. Main project parts

### PC Studio

React/Vite frontend + FastAPI backend. Prototype functions include camera receiving/simulation, inference, zones, tracking/analytics, dataset/training/model tools, ranked simulated signal scenarios, experiment telemetry, camera diagnostics and Junction Network configuration/observability.

### Device camera

ESP32-CAM or similar nodes act as lightweight frame sources. Heavy AI, training, signal-policy logic and analytics belong on the PC side. Several ESP sessions may be saved/streamed, but only one selected source currently feeds the shared live AI/traffic pipeline.

### Junction Network

The Junction Network page can represent several installed/model junctions as nodes and directed links. One junction may be assigned several saved ESP cameras. It can display camera health and current traffic/pedestrian/events/warnings for the junction resolved from the selected live source.

This visualization does **not** mean all junctions are simultaneously inferred. Unobserved junctions intentionally show unavailable live traffic values rather than copied values from the selected source.

### Runtime data

Local datasets, outputs, trained models, labels, camera profiles, zone/settings/signal/network config, histories, and experiment results are valuable working data. They are not source-patch content.

## 4. Understand the data categories

Do not interpret every number as the same type of traffic measurement:

- **Occupancy** — how many relevant detections are present in a sampled frame/region.
- **Flow** — events produced by prototype cross-frame tracks crossing lines or entering/leaving regions.
- **Zone/class observation** — detector-class count inside a polygon for a scenario evaluation.
- **Simulation experiment telemetry** — synthetic numeric simulator output.
- **Network link** — configured topology metadata; not proof that vehicles actually transferred between intersections.
- **Junction node position** — logical PC Studio canvas location; not GPS/geospatial truth.

The lightweight tracker can lose/swap identities in difficult scenes, so track-derived figures remain prototype measurements.

## 5. Signal logic in plain language

The simulated controller uses protected phases. Adaptive/Test modes can evaluate ranked scenarios against observations. Multiple scenarios can be true, but one highest-ranked eligible scenario wins an evaluation. Its action remains bounded by protected timing/order rules.

A scenario may use controller metrics or a class count in a configured zone. These values must be interpreted according to their source; a per-frame count is not throughput.

## 6. Network and future capabilities

AiTL is designed to grow toward stronger live multi-intersection cooperation, emergency priority, pedestrian-aware control, vehicle-class handling and explainable decisions.

Supporting features have different completion levels. `PROJECT_SCOPE.md` is the authority. A configured junction/link/camera assignment is not proof that simultaneous live multi-junction AI or cooperative physical control is operating.

## 7. Routine Windows workflow — use one command

For normal update, full automated validation and PC Studio launch, use:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

This is the default workflow. You normally do **not** need to manually:

- run `git pull` separately;
- maintain a list of regression scripts;
- kill an old AiTL backend/frontend on ports 8000/5173;
- reinstall Python/Node dependencies on every run;
- run frontend typecheck/build separately;
- start backend/frontend separately.

The helper protects tracked local edits before updating, preserves untracked runtime data, reloads itself after the pull, runs cheap compile/structure/release checks first, and then performs the full regression/typecheck/build/smoke/startup workflow.

For speed, a normal Git update now refreshes backend dependencies only when the backend requirement manifests changed, and refreshes frontend dependencies only when `package.json`/`package-lock.json` changed or `node_modules` is missing. Tests/build/smoke are **not** skipped when dependency installation is skipped.

If an unrelated program owns port 8000/5173, the runner refuses to terminate it automatically.

If the local Python/Node environment was manually damaged or you suspect a dependency problem, force refresh with:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -RefreshDependencies
```

Use individual commands from `LOCAL_TESTING.md` only when diagnosing the stage that failed.

## 8. Git/runtime-data safety

Do **not** use `git clean -fd` as a routine fix. Do not delete datasets, outputs, models, labels, configs or caches merely to make an update run.

If the runner reports tracked local edits, inspect/commit/restore those edits deliberately. Untracked runtime data shown by `git status` is expected and does not need to be removed just because it appears in the status output.

Before sharing source changes, confirm no datasets, outputs, trained models, secrets, caches, or personal/private media were committed.

## 9. Testing a candidate

The normal runner covers the automated suite. The current candidate's `TEST_READY_CHECKLIST.md` contains the manual behavior checks automation cannot prove, such as physical ESP performance or visual interaction.

Cheap repository/release checks intentionally run before dependency refresh, so version/document/structure errors should appear near the top rather than after lengthy install output.

Automated tests make a candidate test-ready; they do **not** make it the passed baseline.

When reporting a problem, copy the first failed section and error from the runner rather than rerunning many unrelated commands. That makes diagnosis faster.

## 10. Owner acceptance rule

The owner is the only authority that promotes a candidate.

If root `VERSION` shows `version` different from `passed_baseline`, the candidate remains unaccepted. After testing, explicitly state that the candidate passes/works before a later repository update changes `passed_baseline`.

## 11. Data privacy

Traffic imagery may include people, vehicles, license plates, or school surroundings. Before storing/sharing real data:

- follow school/local privacy rules;
- minimize identifiable faces/plates;
- prefer synthetic/demo media when possible;
- keep only data needed for the experiment;
- never place sensitive datasets in a source patch.

## 12. Safety boundary

Appropriate uses include classroom demonstrations, model junctions, recorded/synthetic analysis, local computer-vision experiments, and supervised simulated decision support.

Out of scope: public-road control, production signal-cabinet integration, bypassing safety systems, or relying on an unsupported AI detection as the only safety layer.
