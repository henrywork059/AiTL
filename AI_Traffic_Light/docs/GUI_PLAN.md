# PC Studio UI Structure and Presentation Guidance

This is durable UI guidance for the current PC Studio architecture. It is not an old placeholder plan and does not own release state.

## 1. Product role

PC Studio is the local operator/developer/reviewer interface for:

- camera receiver and simulation;
- live inference/overlays;
- zones;
- traffic logic and decision explanation;
- occupancy/flow analytics;
- Simulation Lab experiments;
- dataset capture/review;
- training/model registry;
- settings/logs.

Future multi-intersection UI should extend these patterns rather than create a separate unrelated application.

## 2. Navigation/page ownership

`App.tsx` coordinates navigation/top-level shared state. Page-specific state/behavior belongs in `src/pages/`, reusable presentation in `src/components/`, API access in the typed API layer, and common scheduling/error behavior in shared libraries.

Current function availability belongs in `PC_STUDIO_FUNCTION_LIST.md`; exact candidate details belong in `START_HERE.md`.

## 3. Live AI / camera presentation

The live frame is the primary visual surface. Preserve alignment between:

- source frame;
- detection boxes/labels;
- saved zone geometry;
- simulated signal overlay.

Canonical boxes/zones must not be overwritten with browser/canvas coordinates. Display scaling is presentation-only.

Useful controls/status should be compact and task-oriented: source state, model/confidence/visibility, zones, phase/decision, capture, and diagnostic status. Avoid covering important roadway/crossing regions with oversized chrome.

## 4. Traffic Logic presentation

Traffic Logic should separate concerns with compact tabs/panels:

- Live Decision;
- Signal Timing;
- Scenario Rules;
- Test & Safety;
- History.

Scenario editing should use a list + selected editor rather than expanding every scenario into one long form. Show rank, trigger conditions, response, target phases, persistence/cooldown, and current eligibility/winner explanation.

Explainability should be readable first, with detailed observed values/context available on demand. Do not dump raw controller state into the main view.

## 5. Simulation Lab presentation

Keep the experiment workspace bounded to one practical page using:

- top-level run controls;
- stored-run selector;
- Summary / Waiting & queues / Throughput / Signal behavior / Raw samples tabs;
- toggles/dropdowns for mode/sample display;
- pagination/internal scrolling for raw samples.

Prefer comparisons that show Fixed vs Adaptive (and later Independent vs Cooperative) with clear metric direction/units and configuration snapshot. Do not imply synthetic results are public-road performance evidence.

## 6. Analytics presentation

Keep **Occupancy** separate from **Flow / Tracks** because they have different semantics. Make units/data source clear and avoid combining sampled counts into throughput.

When future network metrics appear, distinguish configured topology, transfer events, arrival predictions, and network aggregates.

## 7. Dataset/training/model tools

Dataset Capture, Review/Label, Training, and Model Registry are working prototype workflows, not placeholder pages. UI changes should preserve explicit destructive confirmation, status/error visibility, and separation between source captures, labels, managed datasets, training runs, and model registry state.

## 8. Network/cooperation UI direction

The current network foundation is API/config-first. A later network UI should support generic N-intersection topology without hard-coding exactly A/B.

Recommended grouped views:

- **Intersections** — ID, label, sources, zones/profile, enabled state;
- **Links** — source/destination approaches and prototype travel time;
- **Live network** — per-intersection state + neighbour/arrival context;
- **Decision details** — why a local/cooperative scenario won;
- **Network experiment** — same-seed comparison and aggregate metrics.

Do not show configured links as animated measured traffic until explicit transfer events exist.

## 9. Emergency/pedestrian/class explanation direction

Future views should expose context without adding a separate dashboard for each capability. Reuse structured decision details with compact sections for:

- pedestrian demand/service/clearance;
- vehicle classes;
- neighbour context;
- emergency event/priority lifecycle;
- resulting bounded action and timing.

Every source should show provenance where confusion between AI/simulation/manual input is possible.

## 10. Design-system rules

Use the shared design-system tokens/components. Preserve light/dark/system appearance, restrained Material-derived hierarchy, semantic action states, readable contrast, and bounded density.

Avoid page-local neon/gradient styling, giant decorative cards, excessive rounded containers, or color used without semantic meaning.

## 11. Loading/error/empty states

Every data-dependent page should have meaningful states for:

- loading/refreshing;
- no source/data/config;
- stale/unavailable observation;
- backend/API error with useful error/request context;
- destructive-action confirmation/result;
- simulation/manual source labeling where relevant.

Fallback presentation must not hide a real backend mutation error.

## 12. Safety wording

Signal graphics, phase labels, network links, emergency test events, and decisions are simulation/prototype displays. UI copy must not imply physical/public-road signal authority.
