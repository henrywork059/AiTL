# Code Structure Rules

The project should be built from small, debuggable modules.

## Core rule

```text
One file = one clear responsibility.
One function = one clear action.
One patch = one logical change.
```

## Frontend structure

```text
src/
  App.tsx                 page switching only
  layout/                 shell/sidebar/header layout
  pages/                  page-level templates
  components/             reusable UI pieces
  constants/              navigation/function registry
  lib/                    API client/logger/helpers
  types/                  shared TypeScript app types
```

Do not put camera logic, inference logic, traffic logic, and dataset logic all inside `App.tsx`.

## Backend structure

```text
app/
  main.py                 app wiring only
  routes/                 HTTP endpoints
  services/               business logic
  core/                   logging/errors/middleware/response envelope
```

Route files should stay thin. Service files should be easy to unit test.

## Debugging requirement

Every future non-trivial function should include at least one of:

```text
- structured log message
- request ID propagation
- project error code
- clear return status
- docstring explaining the placeholder or implementation boundary
```

## 0_0_4 template files

The 0_0_4 patch adds the PC Studio page layout and API placeholders. It is acceptable that many pages do not do real work yet. The goal is to confirm the architecture before implementation.
