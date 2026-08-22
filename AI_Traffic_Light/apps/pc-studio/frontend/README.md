# PC Studio Frontend

React/Vite GUI for the AiTL local prototype. Root `AI_Traffic_Light/VERSION` defines release state; this README describes frontend ownership and current capability families without owning the candidate/baseline snapshot.

## Working surfaces

PC Studio currently includes:

- Dashboard;
- Camera Sources;
- Live AI;
- Zone Editor;
- Traffic Logic;
- Simulation Lab;
- Traffic Analytics;
- Dataset Capture / Review & Label;
- Train / Export;
- Model Registry;
- Settings;
- Logs.

See `../../../docs/PC_STUDIO_FUNCTION_LIST.md` for detailed current functions.

## Traffic Logic UI

Traffic Logic uses compact grouped surfaces:

- **Live Decision** — active phase/decision, current winner and arbitration context;
- **Signal Timing** — protected phase policy/timing configuration;
- **Scenario Rules** — ranked scenario list + selected-scenario editor;
- **Test & Safety** — dry-run/Test-mode inputs, incident/reset tooling;
- **History** — signal-decision history.

Ranked scenarios may use controller metrics or zone/class observations. The UI should distinguish triggered, winner, suppressed, inactive, unavailable, persistence/cooldown, and current observed values without dumping raw state into one long page.

## Simulation Lab UI

Simulation Lab keeps dense telemetry grouped behind Summary / Waiting & queues / Throughput / Signal behavior / Raw samples tabs. Stored-run selection, toggles/dropdowns, pagination, and internal scrolling keep the experiment view bounded.

Synthetic results must be labeled as local simulation evidence, not public-road performance/safety evidence.

## Network/explanation direction

The current network foundation is backend/API-first. A future UI should support generic N-intersection configuration and per-intersection/network views without assuming exactly two intersections.

Until explicit transfer/cooperation behavior exists, configured links must not be visualized or described as measured traffic transfer. Structured decision details should show neighbour/emergency/pedestrian/class context with provenance where appropriate.

## Frontend ownership

```text
src/App.tsx          top-level composition/navigation/shared coordination
src/pages/           page behavior/state
src/components/      reusable presentation
src/api.ts           typed domain API functions
src/lib/apiClient.ts shared envelope/error handling
src/lib/useSerialPolling.ts non-overlapping periodic async refresh
src/types.ts/types/  shared contracts
src/constants/       navigation/release fallback metadata
src/styles/          shared design system
```

Do not place page-specific domain logic in `App.tsx`. Do not recreate API shapes ad hoc inside pages.

## Polling

Async periodic work that can overlap should use the shared serial polling mechanism or an equivalent self-scheduling loop. A slow backend request should not cause a second same-loop request to start before the first settles.

## Image/overlay coordinates

Detection boxes and zones remain canonical in source/reference coordinates. Browser/canvas scaling is presentation-only and must not be persisted as the source geometry.

## Visual system

Use the shared design system under `src/styles/` and its role-based semantics. Keep neutral surfaces dominant, interaction colors purposeful, semantic success/warning/error distinct, and traffic-signal colors separate from generic app state.

Avoid page-local neon/gradient/glass dashboard themes or giant decorative cards. Dense technical information should be grouped with hierarchy, details, tabs, filters, and bounded scrolling.

## Error/fallback behavior

Loading/offline/read-only fallbacks may keep the UI understandable, but mutation failures should not be silently hidden. Preserve backend stable error/request context where useful for debugging.

## Local frontend run

```powershell
npm ci
npm run typecheck
npm run build
npm run dev
```

Use `../../../docs/LOCAL_TESTING.md` for the current candidate's full validation sequence.

## Safety boundary

Signal graphics, decisions, network context, experiments, and emergency/accessibility Test-mode inputs are prototype/simulation UI. The frontend is not connected to physical/public-road traffic infrastructure.
