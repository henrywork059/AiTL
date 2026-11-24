# M.E.S.H. — development roadmap and update schedule

Owner-approved direction: 24 November 2026. This is the living engineering plan, not a release record or evidence of completed work. Public project name: M.E.S.H. (Multi-intersection Ecosystem for Smart Harmony; 路有靈犀). Retain AiTL in existing repository paths, APIs and identifiers.

## 1. Approved decisions

- Major restructuring is permitted where a documented architectural problem justifies it; preserve working behavior, saved data and API contracts unless an approved migration requires otherwise.
- Replace the existing simulation engine through a staged migration, not a simultaneous rewrite of traffic logic, rendering and hardware.
- Completely redesign PC Studio, using compact hardware-first workflows and a consistent visual system.
- Prioritize physical hardware integration, reliability and diagnostics over new simulation or cosmetic features.
- Evaluated open-source dependencies are permitted. Check license, maintenance, security, Windows compatibility, performance and integration costs before adoption.

## 2. Operating and release rules

Work only on `feature/interactive-3d-simulation` unless the owner explicitly authorizes another branch. Never push to or merge into main, change the passed baseline, or activate physical signal control without the required owner approval. Public-road signal control remains out of scope; any physical outputs are limited to explicitly authorized controlled model demonstrations.

Read [AGENTS.md](../AGENTS.md), [PATCH_PLAYBOOK.md](PATCH_PLAYBOOK.md), [PROJECT_SCOPE.md](PROJECT_SCOPE.md) and [VERSION](../VERSION) for authority. The roadmap governs task selection, not release state. Before changes, inspect the current feature-branch HEAD, version, relevant source, tests and CI. Stop if the branch changes unexpectedly.

For each new PC candidate: reproduce or establish the problem, implement the smallest coherent fix (or justified staged refactor), add behavior-focused regressions, execute available checks, increment Z exactly once, synchronize release surfaces, commit atomically where possible, push with a verified parent, report SHA and actual test results, and provide the Windows acceptance command. X/Y changes and stable promotion require explicit owner approval. Planning-only documentation commits do not constitute a new PC candidate. CI success is not owner or hardware PASS.

## 3. Schedule and dependency gates

Dates are target planning windows, not commitments or permission to bypass gates. Work can overlap if interfaces are stable and safety is preserved. If a gate is blocked, prioritize removing the blocker, not marking the phase complete. The order below supersedes the older V035 roadmap priorities.

| Phase | Target window (Hong Kong time) | Main work | Exit gate |
| --- | --- | --- | --- |
| P1 — Hardware foundation | 24 Nov–Dec 2026 | Validate current candidate; ESP lifecycle, reconnect, stale-frame isolation, diagnostics, module interface, camera and bench peripherals | Focused regressions, CI, owner Windows/ESP validation; physical module tests only with authorized setup |
| P2 — Architecture restructuring | Dec 2026–Jan 2027 | Separate device transport, observations, perception, decisions, safety and outputs; preserve API and config compatibility | Contract and migration tests, no duplicate owners, documented measured trade-offs |
| P3 — Simulation replacement | Dec 2026–Feb 2027 | Evaluate traffic and rendering engines, migrate through adapters, establish deterministic scenarios and multi-intersection movement | Parity with essential behaviors, seeded repeatability, lifecycle and interlock tests, acceptable resource usage |
| P4 — Interface redesign | Jan–Feb 2027 | Hardware-first dashboard, device setup/diagnostics, network, simulation, AI and experiments | Functional browser checks, accessible responsive layout, stable camera/editor workflows, owner acceptance |
| P5 — Experimental validation | Jan–Mar 2027 | Controlled model junction, hardware endurance, perception evaluation, fixed-time/adaptive/cooperative comparisons, report evidence | Reproducible evidence with provenance, methods, uncertainty, limitations and safety checks |

Competition planning checkpoints recorded at approval: Hong Kong Science Fair registration 29 Nov 2026; Hong Kong Student Science Project Competition nomination 4 Dec 2026; Hong Kong Youth Science and Technology Innovation Competition registration 15 Jan and submission 22 Jan 2027; Hong Kong Science Fair materials 28 Feb 2027; Hong Kong Student Science Project Competition submission 9 Mar 2027. Geneva participation route and timing remain to be confirmed. Verify official requirements before each submission. Do not distort the engineering validation to meet a deadline.

## 4. Ordered engineering backlog

Status vocabulary: PLANNED, IN PROGRESS, BLOCKED, CANDIDATE (not accepted), ACCEPTED (explicit owner PASS). These statuses describe backlog progress, not certified deployment readiness. All unmarked future work is proposed. Each task should have a concrete outcome and testable acceptance criteria.

| ID | Priority | Status at plan adoption | Task and acceptance criteria |
| --- | --- | --- | --- |
| H01 | P0 | CANDIDATE | Post-read ESP cancellation guard; see [0_5_44 patch](PATCH_0_5_44.md). Owner Windows/ESP PASS outstanding at adoption. |
| H02 | P0 | PLANNED — next | Audit ESP worker lifetime and session transitions: blocked socket open/read, stop timeout, old-worker cleanup, reconnect/restart, mode switch. Reproduce late publication/status corruption and prove retired workers cannot affect replacement sessions. |
| H03 | P0 | PLANNED | Audit frame/cache freshness and source identity during disconnect, reconnect, replacement and simulation transitions; reject stale/retired inputs with deterministic regressions. |
| H04 | P0 | PLANNED | Restore a reproducible test checkout/environment; verify existing CI, full offline suite and Windows owner workflow; do not conflate isolated tests with end-to-end PASS. |
| H05 | P1 | PLANNED | Measure ESP camera FPS, frame age, latency, CPU/memory, packet sequence gaps and reset/weak-Wi-Fi recovery under documented settings. |
| H06 | P1 | PLANNED | Define modular device capabilities, configuration, health, timeouts and PC-owned connection lifecycle using existing camera manager rather than a duplicate registry. |
| H07 | P1 | PLANNED | Bench-only lighting/speaker interfaces with safe disabled defaults, bounded output and disconnect behavior. Optional modules cannot compromise the core. |
| A01 | P0 | PLANNED | Audit protected phases, pedestrian clearance, emergency evidence, conflict matrix and stale data behavior; require no conflicting permissions in tested virtual scenarios. |
| A02 | P1 | PLANNED | Establish explicit observation and source contracts shared by physical devices and simulation; preserve source IDs, timestamps, coordinate systems and provenance. |
| A03 | P1 | PLANNED | Isolate tracking and traffic state per intersection; validate counts/identity and avoid unsupported cross-camera fusion claims. |
| A04 | P1 | PLANNED | Refactor oversized modules only where boundaries and tests justify it; remove verified dead code; centralize transport/configuration and shared UI networking. |
| S01 | P1 | PLANNED | Evaluate Eclipse SUMO or another suitable traffic engine and Three.js or another suitable renderer. Record alternatives, license, dependencies, Windows setup and benchmarks before choosing. |
| S02 | P1 | PLANNED | Implement a migration adapter and deterministic state/clock contract; keep existing engine available during validation and retain rollback path. |
| S03 | P1 | PLANNED | Replace rendering/agent lifecycle with real 3D road geometry, diverse vehicles, articulated pedestrians and continuous movement; test exit/respawn, turning, camera views and pause/resume. |
| S04 | P1 | PLANNED | Validate multi-junction vehicle transfer, demand, queues, spillback and protected signal coordination; compare seeded results and preserve experiment exports. |
| U01 | P1 | PLANNED | Audit current workflows and design a new shell around Dashboard, Devices, Network, Simulation, AI Lab and Experiments. Minimize secondary labels and preserve functional accessibility. |
| U02 | P1 | PLANNED | Implement redesign incrementally; typed API reuse, non-overlapping polling, responsive navigation, clear connection/mode/signal/error status and browser tests. |
| E01 | P1 | PLANNED | Build authorized model-junction prototype and test fail-safe behavior, module isolation, connection loss and repeatability. No public-road actuation. |
| E02 | P1 | PLANNED | Run fixed-time/local adaptive/cooperative comparisons under identical scenario settings and seeds. Record wait, queue, throughput, pedestrian clearance, emergency delay and fairness. |
| E03 | P1 | PLANNED | Evaluate AI precision/recall, latency and reliability using labeled data; report limitations and distinguish measured data from synthetic observations. |
| E04 | P2 | PLANNED | Record endurance/resource use, emissions estimates with assumptions, costs and results in the master competition report. |
| E05 | P2 | PLANNED | Seek documented professional and government feedback; no partnership or approval claim until evidenced. Drone integration remains exploratory and subject to authorization. |

Safety/security issues may interrupt the order. H04 and A01 can proceed alongside H02/H03. Start engine migration or new frontend work only after defining the affected interfaces; do not introduce unrelated rewrites into a hardware candidate.

## 5. Evidence and acceptance targets

Proposed targets, not achieved results: zero conflicting permissions in tested scenarios; no visible vehicle/pedestrian lifecycle defects; identical seeded simulation results; eight-hour endurance test; at least 10% mean waiting-time and 20% emergency-delay reduction versus declared baseline, subject to safety and fairness. Evaluate actual feasibility and report negative or null outcomes. Initial proposed research design: six scenarios × three controllers × 30 seeds = 540 runs; execute and record the runs before claiming results.

For every experiment record code SHA, settings, seeds, sample size, units, baseline, raw artifacts, method and uncertainty. Classify results as measured, actually executed simulation, estimate with assumptions, external literature, proposed, or illustrative/synthetic. Never claim a pilot, partnership, certification, measured improvement or hardware test that did not happen.

## 6. How future updates use this document

1. For open-ended maintenance/development tasks, read this roadmap and select the highest-priority unfinished item whose dependencies are satisfied. Explicit owner tasks override this default, but not safety/release gates.
2. Identify the backlog ID in the patch note and handoff; note the intended outcome and focused regression before edits.
3. Update only affected backlog status, blocker and evidence links when the state materially changes. Candidate delivery is not acceptance; link the actual patch/commit and test evidence. Never rewrite historical release records.
4. If local execution or hardware is unavailable, state precisely what was tested and what remains blocked; avoid repeated speculative patches or empty commits. Escalate safety, acceptance and major scope decisions to the owner as required.
5. Review scheduling and dependencies after each phase gate or significant owner decision; keep this as the single engineering roadmap rather than spawning parallel plans.

### Progress log

| Date | ID | Evidence / outcome | Next action |
| --- | --- | --- | --- |
| 2026-11-24 | H01 | Candidate [8256bd2](https://github.com/henrywork059/AiTL/commit/8256bd2f3cc3984588884e5eccf3553a11add142); [CI run 45355984796](https://github.com/henrywork059/AiTL/actions/runs/45355984796) completed successfully. Owner acceptance not established. | Windows/ESP validation; H02 worker lifecycle audit. |

## Historical V035 milestones retained as hardware test requirements

Sustained VGA/QVGA measured FPS; visible end-to-end latency; ESP reset/reconnect recovery; weak-Wi-Fi reconnect behavior; simulation pause/resume; backend relay/parser CPU load. The older next steps (independent buffers/routing, intersection assignment and tracker isolation, controlled model-junction output abstraction, multi-intersection orchestration/evidence UI) are covered by the backlog above. Public-road signal control remains out of scope.
