# Human Guide

This guide is for the project owner, students, teachers, and reviewers using **AI Traffic Light (AiTL)**. It is intentionally version-agnostic; read root `VERSION` and `START_HERE.md` for the current candidate.

## 1. What AiTL is

AiTL is a local prototype for studying computer vision and adaptive traffic-light **simulation**.

```text
camera or synthetic scene
→ local object detection
→ zones/tracking/counting
→ simulated signal scenario evaluation
→ explanation, analytics, and experiment results in PC Studio
```

It also contains a local dataset/training workflow and a developing multi-intersection/network foundation.

AiTL is **not** a certified public-road traffic-control system and does not connect its simulated decisions to public traffic infrastructure.

## 2. Where to start

For current project state:

1. Read `../VERSION`.
2. Read `START_HERE.md`.
3. Read `PROJECT_SCOPE.md` to distinguish implemented, foundation, and planned capabilities.
4. Use `LOCAL_TESTING.md` / `TEST_READY_CHECKLIST.md` when testing the current candidate.
5. Use `DOCUMENTATION_MAP.md` if documents appear to disagree.

## 3. Main project parts

### PC Studio

React/Vite frontend + FastAPI backend. Current prototype functions include camera receiving/simulation, inference, zones, tracking/analytics, dataset/training/model tools, ranked simulated signal scenarios, experiment telemetry, and network/explanation foundation.

### Device camera

ESP32-CAM or similar nodes act as lightweight frame sources. Heavy AI, training, signal-policy logic, analytics, and future network cooperation belong on the PC side.

### Runtime data

Local datasets, outputs, trained models, labels, zone/settings/signal/network config, histories, and experiment results are valuable working data. They are not source-patch content.

## 4. Understand the data categories

Do not interpret every number as the same type of traffic measurement:

- **Occupancy** — how many relevant detections are present in a sampled frame/region.
- **Flow** — events produced by prototype cross-frame tracks crossing lines or entering/leaving regions.
- **Zone/class observation** — detector-class count inside a polygon for a scenario evaluation.
- **Simulation experiment telemetry** — synthetic numeric simulator output.
- **Network link** — configured topology metadata; not proof that vehicles actually transferred between intersections.

The lightweight tracker can lose/swap identities in difficult scenes, so track-derived figures remain prototype measurements.

## 5. Signal logic in plain language

The simulated controller uses protected phases. Adaptive/Test modes can evaluate ranked scenarios against observations. Multiple scenarios can be true, but one highest-ranked eligible scenario wins an evaluation. Its action remains bounded by protected timing/order rules.

A scenario may use controller metrics or a class count in a configured zone. These values must be interpreted according to their source; a per-frame count is not throughput.

## 6. Network and future capabilities

AiTL is being designed to grow toward:

- multi-intersection cooperation;
- emergency priority;
- stronger pedestrian-aware control;
- different vehicle-class handling;
- explainable decisions.

Some supporting foundations already exist, but these capabilities have different completion levels. `PROJECT_SCOPE.md` is the authoritative capability-status guide. Do not present a planned/foundation feature as operational.

## 7. Safe GitHub patch workflow

A patch ZIP contains **changed files only**.

1. Download the patch ZIP and manifest.
2. Verify the ZIP/member list if desired.
3. Extract the ZIP.
4. Upload the extracted files into their matching paths under `AI_Traffic_Light/` on GitHub `main`.
5. Do not upload only the ZIP as a repository file.
6. Use a clear commit message describing the candidate and change.

Before uploading, confirm the patch contains no datasets, outputs, trained models, secrets, caches, or personal/private media.

## 8. Safe Windows update after GitHub upload

Stop the running backend/frontend first. From the repository root:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Do **not** use `git clean -fd`. If `git status` shows local work you care about, inspect/preserve it before pulling rather than deleting it.

The repository's `scripts/update_test_run.ps1` may be used when the current candidate documentation says it is appropriate.

## 9. Testing a candidate

Use the exact current commands in `LOCAL_TESTING.md`. A normal validation includes:

- Python compile/structure checks;
- backend regression scripts;
- live smoke with backend running;
- frontend typecheck/build;
- manual PC Studio acceptance checks;
- repository/ZIP hygiene checks.

Automated tests make a candidate test-ready; they do **not** make it the passed baseline.

## 10. Owner acceptance rule

The owner is the only authority that promotes a candidate.

If root `VERSION` shows `version` different from `passed_baseline`, the candidate remains unaccepted. After testing, the owner should explicitly state that it passes/works before a later repository update changes `passed_baseline`.

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
