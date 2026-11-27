# V0575 — Independent source-qualified capture, training-safety and evidence-verification candidate

Candidate 0_5_75; previous 0_5_74; accepted baseline 0_5_0. Independent concurrent P3/P4/P5 progress, partial Updates 30/33/37/38. Updates 31 and 36 remain delivered candidates from 0_5_74. 30/39 delivered candidate milestones (76.9%), not owner acceptance. Update 28 / S04 remains gated.

## Substantive implementation

P3: NativeProjectionView remounts source-specific client workspace when source ID changes; previous native view/playback state retires without changing legacy simulator default. P4: Dataset capture checks latest backend frame against optional expected source ID and upload/simulation mode, rejecting mismatch with HTTP 409 before writing; existing callers remain supported. The capture page requires current non-stale selected feed, sends source/mode identity and verifies returned record; status errors withdraw stale capture readiness. Training and managed-dataset polling now use strict, scoped reads and clear prior ready states on errors; Start training rechecks live availability and managed dataset readiness, with no CI execution of actual YOLO training. Review rejects false ready/split responses. Explicit evaluation-only (detector_input_eligible=false) native captures are excluded from managed YOLO train/validation, with separately reported exclusion count and preserved legacy eligibility semantics. Side A/B region editor now remounts SVG drag vertices on side switch to retire stale native hit geometry. The independent two-camera race regression permits legitimate fail-closed expired cache and still rejects wrong-source publication.

## Qualification and inspected browser evidence

P4 exact real-clock Windows Edge browser CI 46025031969 PASSED on application tree b6c0f1e2ca5584c81fd0758478e4f730cac959ce. It exercised actual pointer input, source-change capture rejection and recovery, decoded synthetic HTTP preview, stale/ready/error training transitions, saved crosswalk regions and side-specific vertex repaint, junction topology and source ownership, review labels/build/delete, render/rollback. Verified artifact 15210369050 SHA-256 6bf6a116c42999f2d226e3f0cdcb0473dbc3aff675920939278778ba964a1fba, with capture, training, crosswalk, junction and review screenshots actually inspected. Synthetic API and HTTP image fixtures only; not a physical ESP or trained detector. Standard CI 46022866121 PASSED full offline, seeded batch, build/audit at prior implementation tree; exact latest CI 46025214608 passed offline regressions including deterministic camera race correction, and was executing the seeded batch during release preparation. Release commit CI and owner Windows PASS remain pending.

## Reproducible synthetic experiments

P5: Read-only verifier validates 43 manifest member hashes and reconciles every raw fixture's 36 primary policy rows, 96 local fairness rows, 732 timeline ticks across four policy arms (2928 arm-samples), and 19,725 normalized decision records. Verifier rejects modified CSV metrics, timelines or decisions even when their manifest hashes are recomputed; busy 4/4 repeat scenarios reconcile. Independent actual synthetic experiment archive 15209410327 from standard CI 46021591042 SHA-256 bbb9eefe32d796c90b3cee43f21716f2cf714f872690e6f43c8bd2b5fc1a4598 passed archive digest and content reconciliation. 4 seeds x 3 densities x 120 seconds; primary fixed/adaptive/cooperative, pedestrian-aware secondary. Cooperative versus adaptive has higher pedestrian wait in 11/12 cases: light 4/4, normal 3/4, busy 4/4; busy average +32.125 person-s, while vehicle wait average -305.875 vehicle-s. Actual executed synthetic queue model, not field results, proof of physical safety or native/legacy parity. Existing timeline/decision semantic checks cover selected exported fields, not every raw observation.

## Mandatory migration / safety boundaries

S04 remains OPEN. Existing native archive 15204881978 and CI 46012562415 qualified 11 synthetic captures/44 mirrored decoded views with a palette control, not a trusted trained detector. Native/reference finite passages each 8 vehicles and 14 pedestrians, but normalized waits remain different: native/reference 129.4/144 vehicle-agent-s and 15.4/57.2 pedestrian-agent-s. Production coordinate calibration or explicit synthetic-only contract, common wait estimand, trained holdout/detector proof, owner-PC Windows/resource budget and rollback acceptance remain missing. Freeze optional geometry polish. Legacy simulator stays default; native trial is opt-in. No public-road actuation, stored-data migration, accepted baseline promotion, main merge, or owner PASS claim.

## Windows owner qualification

From repository root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Check footer 0_5_75 Candidate, two physical sources and simulation-mode handoff (authorized test only); verify no stale preview, Side A/B polygon save/fail/reload and real pointer hit, capture source-switch rejection with no file write, status-error recovery, managed dataset exclusion of evaluation-only samples, training ready/stale/failure recovery and raw evidence integrity. Use disposable test data and back up saved profiles. Do not run real YOLO training or connect public-road controllers as part of CI. Owner must explicitly confirm PASS.
