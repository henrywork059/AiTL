# Code Structure Rules

AiTL should stay modular enough that a developer or AI agent can identify one clear owner for each behavior.

## Core principles

```text
One module = one cohesive responsibility.
Routes translate HTTP; services own behavior.
UI pages coordinate page behavior; components render reusable pieces.
Shared project facts should have one authoritative source when practical.
A patch should solve one logical problem without unrelated rewrites.
```

File length alone is not a reason to split a module. Split when responsibilities, side effects, or test boundaries are mixed.

## Backend structure

```text
apps/pc-studio/backend/app/
  main.py                 FastAPI creation/wiring only
  models.py               Pydantic request/response models
  core/
    api_response.py        standard envelope helpers
    error_codes.py         stable ErrorCode definitions
    exceptions.py          AppError/global handlers
    logging_config.py      structured logging/buffer setup
    middleware.py          request context/request ID
    project_version.py     validated root VERSION metadata
  routes/                  thin HTTP handlers
  services/                camera/data/model/training/zone/traffic business logic
```

### Backend boundaries

Keep these out of routes when possible:

- filesystem operations;
- training/inference algorithms;
- dataset construction;
- model registry state;
- zone/traffic calculations;
- multi-step rollback/cleanup behavior.

Route handlers may validate/translate HTTP-level input and invoke a service.

Backend release labels must use `core/project_version.py`; do not duplicate literal project versions in health/smoke/template/app wiring.

## Frontend structure

```text
apps/pc-studio/frontend/src/
  App.tsx                 page switching and top-level coordination
  api.ts                  domain API functions/fallback values
  layout/                 shell/navigation layout
  pages/                  page-level behavior
  components/             reusable visual/interaction components
  constants/              navigation/function/release metadata
  lib/                    API client, logging, error helpers
  types.ts                shared domain/API types
  types/                  app-specific type modules
```

### Frontend boundaries

Do not move camera, inference, dataset, or traffic business rules into `App.tsx` just because state is already available there. Pass state/callbacks to pages or extract a focused helper/component.

Keep domain response types centralized instead of creating slightly different local interfaces per page. Keep the frontend release mirror in `constants/projectVersion.ts`; current version surfaces should import it rather than repeat release literals.

## CV coordinate rule

Canonical detection boxes use original image coordinates. Persistent zones use the validated reference coordinate system. Display layers may scale those values to the rendered image/canvas.

Do not persist browser/canvas pixels as the canonical record.

## State and side-effect rule

When a workflow mutates user data, the module owning the workflow should make the whole state transition understandable and testable. Examples include:

- capture image + metadata + optional labels;
- managed YOLO build + staleness state;
- training run + model registry discovery;
- runtime settings/zone persistence.

Prefer explicit return state after a mutation so the UI can refresh from authoritative backend data.

## Refactor heuristic

Consider extraction when a module:

- performs unrelated workflows;
- repeats the same validation/constant in multiple places;
- requires duplicated error handling;
- cannot be unit-tested without unrelated I/O;
- gains a second distinct state machine.

Do not introduce abstraction layers with no current reuse or test benefit.

## Debugging requirement

Non-trivial backend behavior should expose at least one useful diagnostic mechanism:

- structured log context;
- request ID propagation;
- stable error code;
- explicit status/result data;
- focused test coverage.

Frontend failures should preserve actionable backend error messages/codes through the shared API client.


## Traffic analytics ownership

Keep responsibilities separated:

```text
services/traffic_logic.py      one-frame counting + simulation recommendation
services/traffic_history.py    bounded persistent occupancy history/query/export
services/traffic_recorder.py   background sampling lifecycle
routes/traffic.py              thin HTTP translation only
frontend TrafficAnalyticsPage  analytics page coordination
TrafficHistoryChart            reusable chart rendering
```

`counting_region` is a zone-schema concept used for analytics only. Per-frame occupancy is not unique flow tracking.
