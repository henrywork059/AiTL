# Code Structure Rules

AiTL should keep one clear owner for each behavior. Routes translate HTTP; services own behavior; UI pages coordinate page behavior; components/helpers own reusable mechanics.

## Backend

```text
apps/pc-studio/backend/app/
  main.py                 FastAPI creation/wiring only
  models.py               Pydantic request/response models
  core/
    api_response.py        envelope helpers
    error_codes.py         stable errors
    exceptions.py          AppError/handlers
    json_store.py          shared atomic UTF-8 JSON read/write primitive
    logging_config.py      structured logging
    middleware.py          request IDs
    project_version.py     validated root VERSION metadata
  routes/                  thin HTTP handlers
  services/                domain behavior/state/filesystem/model logic
```

### Persistence rule

Services own schemas, validation, locks, logging, and stable error mapping. When a service needs replace-style JSON persistence, prefer `core/json_store.py` rather than duplicating temporary-file mechanics. The V024-migrated runtime-settings, zones, and model-registry services and the V025 intersection-network service use this shared atomic persistence path.

Multi-step state transitions that can race inside one process need service-level synchronization. Zone save/read uses one lock; model-registry discovery/default/delete/metadata transitions use a re-entrant lock; intersection/network config validation/cache/persistence uses a re-entrant lock.

### V025 network/explanation ownership

- `services/intersection_network.py` owns generic intersection ids, source mappings, directed links, topology validation, and runtime `config/intersections.json` persistence.
- `services/decision_context.py` is a non-controlling projection that turns current traffic/signal/network state into structured live explanation context.
- `routes/traffic.py` may attach that service-owned context to `/api/traffic/state`, but it must not implement topology validation, signal arbitration, cooperation algorithms, or emergency pre-emption.
- `services/signal_rules.py` remains the sole owner of ranked scenario arbitration and protected phase/timing behavior.

The network foundation is configuration-only in V025. Do not silently create per-intersection signal authority or claim cooperative control from configured links alone.

## Frontend

```text
apps/pc-studio/frontend/src/
  App.tsx                 page switching/top-level coordination
  api.ts                  typed domain API functions
  layout/                 shell/navigation
  pages/                  page behavior
  components/             reusable presentation
  constants/              navigation/release metadata
  lib/
    apiClient.ts           shared API envelope/error handling
    useSerialPolling.ts    non-overlapping periodic async scheduler
  styles/                 design-system tokens/layers
  types.ts / types/       shared domain types
```

### Polling rule

Do not use `setInterval` for async work when a new tick can start before the previous request settles. Use `useSerialPolling` or an equivalent self-scheduling `setTimeout` loop so there is at most one in-flight poll per loop and cleanup cancels future schedules. Live inference already uses a self-serial detection loop; V024 migrates App-level camera and live-context polling.

## CV / analytics invariants

Canonical boxes use original-image coordinates; zones use the validated reference coordinates; display scaling is presentation-only. Occupancy remains per-frame. Unique passage comes only from stable track identity plus counting-line events.

Network links are configuration metadata, not observed flow. A later multi-intersection simulator must use explicit transfer/arrival events rather than treating configured travel time as measured throughput.

Observation provenance must not overclaim perception: simulated/manual events stay labeled as such; AI-derived labels are only what the active detector actually returns.

## Refactor heuristic

Extract shared mechanics when a fact/algorithm is duplicated across multiple modules, when side effects are inconsistently implemented, or when a second caller/test clearly benefits. Do not refactor merely because a file is long.
