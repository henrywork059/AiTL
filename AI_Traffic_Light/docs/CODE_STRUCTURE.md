# Code Structure and Modularity Standard

Patch: **0_0_3**

This document defines how code should be split in **AI Traffic Light** so that the project stays easy to debug, patch, and extend.

## 1. Core principle

Code should be broken into small modules with clear responsibilities.

Avoid files that do all of these at once:

```text
camera capture
AI inference
zone counting
traffic-light decision logic
file saving
API route handling
GUI rendering
logging
```

Each layer should call the layer below it.

```text
API route
→ service function
→ utility/helper/model wrapper
→ shared schema/error/logging helpers
```

## 2. Backend structure

Use this structure for the PC Studio backend:

```text
apps/pc-studio/backend/app/
  main.py                    app factory, middleware, router registration
  models.py                  Pydantic request/response models
  core/
    api_response.py           success/error response helpers
    error_codes.py            central error-code list
    exceptions.py             AppError and exception handlers
    logging_config.py         backend logging configuration
    middleware.py             request ID and request logging middleware
  routes/
    health.py                 health/version endpoints
    mock.py                   mock/fake-data endpoints
    traffic.py                traffic-state endpoints
  services/
    mock_data.py              fake detection/zone generation
    traffic_logic.py          rule-based signal decisions
    yolo_placeholder.py       future AI model service placeholder
```

## 3. Backend responsibilities

### `main.py`

Allowed:

```text
create FastAPI app
configure CORS
configure logging
add middleware
register exception handlers
include routers
```

Not allowed:

```text
AI inference code
traffic-decision code
large route logic
file parsing logic
camera capture logic
```

### `routes/`

Routes should be thin.

Allowed:

```text
read request data
call service functions
return API response
convert AppError to HTTP response through handler
```

Not allowed:

```text
large detection algorithms
zone-counting algorithms
training loops
long file I/O logic
hard-coded UI behavior
```

### `services/`

Services contain the project logic.

Examples:

```text
detection_service.py
zone_counter.py
traffic_logic.py
camera_receiver.py
dataset_capture.py
model_export.py
```

Each service should expose small functions or small classes. One service file should cover one domain.

## 4. Frontend structure

Use this structure for the PC Studio frontend:

```text
apps/pc-studio/frontend/src/
  App.tsx                    page composition only
  api.ts                     domain-specific API functions
  types.ts                   shared frontend types
  mockData.ts                frontend fallback/mock data
  lib/
    apiClient.ts             fetch wrapper and API envelope handling
    errorCodes.ts            frontend error-code constants
    logger.ts                frontend logging helper
  components/
    ControlsPanel.tsx
    DatasetPanel.tsx
    DetectionTable.tsx
    LiveView.tsx
    StatusPanel.tsx
    TrafficLight.tsx
    ZonePanel.tsx
```

## 5. Frontend responsibilities

### `App.tsx`

Allowed:

```text
state composition
page/tab selection
connecting components together
```

Not allowed:

```text
raw fetch calls
large drawing algorithms
business logic
camera stream parsing
complex API error handling
```

### `components/`

Components should be display/control units only.

Allowed:

```text
render props
take callbacks
show placeholder UI
small local state for UI only
```

Not allowed:

```text
model inference
API implementation
file saving logic
shared traffic decisions
```

### `lib/`

Use `lib/` for reusable frontend logic:

```text
apiClient.ts
logger.ts
errorCodes.ts
geometry.ts later
boxScaling.ts later
```

## 6. Maximum practical file size

These are soft limits, not hard rules:

```text
Route file:        ~100 lines
Service file:      ~200 lines
React component:   ~180 lines
Utility file:      ~150 lines
```

If a file grows beyond this, split it by responsibility.

## 7. Debugging requirement

Every important module should log:

```text
startup/config events
API request failures
camera connection failures
model load failures
model inference failures
zone/counting failures
dataset save/export failures
unexpected exceptions
```

Use project error codes for expected failures.
