# Debugging and Logging Guide

Durable debugging guidance for AiTL. This document does not own release state; read root `VERSION` for the current candidate.

## 1. Debugging goals

A useful diagnostic trail should answer:

```text
What happened?
Which page/API/service was involved?
Which source/intersection/frame/run was involved?
Which request caused it?
Which stable error code applies?
What state/config/provenance affected the result?
Can the failure be reproduced deterministically?
```

## 2. Backend logging

Backend logging is configured in:

```text
apps/pc-studio/backend/app/core/logging_config.py
```

Use the project logger:

```python
from app.core.logging_config import get_logger
logger = get_logger(__name__)
```

Prefer concise structured context in `extra`, for example request ID, frame/source/intersection ID, run ID, model ID, stable error code, or operation result. Do not dump entire frames, datasets, model arrays, or large telemetry documents into logs.

## 3. Frontend logging

Use the shared frontend logging/error path rather than scattered ad-hoc `console.log` statements. When possible include endpoint/page context and preserve backend request IDs/error codes so browser and backend diagnostics can be correlated.

## 4. Request IDs

Backend middleware attaches a request ID to API requests. Debug API failures by correlating the same request ID across frontend error handling and backend logs.

```text
1. Reproduce the problem.
2. Record page/action/endpoint and request_id.
3. Check backend logs for request_id.
4. Read the stable error code in ERROR_CODES.md.
5. Inspect the smallest owning service/route.
6. Add a focused regression before/with the fix.
```

Binary/image/CSV responses should also preserve `X-Request-ID`.

## 5. Log useful state, not secrets

Useful examples:

- app startup/shutdown and relevant runtime mode;
- camera source/simulation changes;
- model load/unload/training transitions;
- persistence failures and stable error codes;
- zone/network/signal config save/reset outcomes;
- experiment run creation/deletion/failure;
- traffic decision errors or unexpected unavailable observations;
- API mutation failures.

Do not log:

- passwords, Wi-Fi credentials, tokens, API keys;
- unnecessary personal data;
- full image frames or large base64 payloads;
- large model tensors/arrays;
- entire datasets/training artifacts;
- private local filesystem content unrelated to the error.

## 6. Reproduction strategy

Prefer the smallest deterministic source that reproduces the bug:

1. focused service/unit regression;
2. direct API test;
3. synthetic camera/simulation state;
4. seeded Simulation Lab run;
5. real receiver/model input only when the issue depends on it.

Do not force a live camera or training job into a UI/layout/config bug that can be reproduced with existing simulation/test paths.

## 7. Data-semantics debugging

Before treating a value as wrong, identify its category:

- occupancy sample;
- track-derived flow event;
- zone/class per-frame observation;
- synthetic experiment telemetry;
- configured network metadata;
- structured decision context.

A mismatch caused by comparing two different categories is not necessarily a counting bug.

For source/intersection issues, inspect `source_id`, resolved `intersection_id`, observation provenance, and current network context separately.

## 8. Signal-rule debugging

For an unexpected Adaptive/Test decision inspect, in order:

1. current mode/profile/phase and served time;
2. observation freshness/provenance;
3. scenario condition observed values;
4. persistence state;
5. phase applicability;
6. cooldown state;
7. rank/eligible winner;
8. protected min/max/cycle clamp;
9. pending requested service/incident state;
10. decision history/context.

Do not debug ranked arbitration by adding competing logic in a route/network layer.

## 9. Network-foundation debugging

Configured links currently describe topology only. If network context looks wrong:

- verify intersection IDs are unique;
- verify source IDs resolve to only one intersection;
- verify link endpoints exist and are distinct;
- verify direction/approach fields;
- inspect ignored runtime `config/intersections.json`;
- confirm `cooperative_control_active` remains false unless a later implementation explicitly changes it.

Do not expect configured travel time to generate a vehicle transfer in the current foundation.

## 10. Persistence debugging

Runtime JSON stores may be ignored by Git but remain important user data. When a persistence bug occurs:

- reproduce against a temporary test path where possible;
- verify validation fails before replacing a previously valid config;
- preserve stable error mapping;
- check locking/atomic-write ownership;
- never solve the issue by deleting the user's runtime directory.

## 11. Patch/handoff diagnostics

When a bug is fixed, record:

- symptom;
- owning module/root cause;
- exact behavior changed;
- regression added/run;
- checks not run;
- any runtime data migration/compatibility note;
- owner acceptance step.

See `DOCUMENTATION_MAP.md`, `AI_AGENT_GUIDE.md`, and the current patch/testing docs.
