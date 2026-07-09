# Debugging and Logging Guide

Patch: **0_0_3**

This guide explains how to keep the project easy to debug.

## 1. Logging goals

Logs should help answer:

```text
What happened?
Where did it happen?
Which request caused it?
Which module failed?
Which error code should be searched?
What useful context is safe to show?
```

## 2. Backend logging

Backend logging is configured in:

```text
apps/pc-studio/backend/app/core/logging_config.py
```

Backend modules should create loggers like this:

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)
```

Log useful events:

```python
logger.info('Generated mock detection frame', extra={'frame_id': frame_id})
logger.warning('Model requested before load', extra={'error_code': 'ATL-DETECT-001'})
logger.exception('Unhandled backend exception', extra={'error_code': 'ATL-COMMON-000'})
```

## 3. Frontend logging

Frontend logging helpers live in:

```text
apps/pc-studio/frontend/src/lib/logger.ts
```

Use them instead of scattered `console.log` calls.

```ts
logInfo('api', 'Loaded mock frame')
logError('api', FrontendErrorCodes.API_FETCH_FAILED, error, { endpoint })
```

## 4. Request IDs

Backend middleware attaches a request ID to each request.

Use request IDs when debugging:

```text
1. User reports problem.
2. Check frontend console for request_id or endpoint.
3. Search backend logs for same request_id.
4. Search error code in docs/ERROR_CODES.md.
5. Fix the smallest responsible module.
```

## 5. What to log

Log these:

```text
app startup
API request failure
camera connection/disconnection
camera frame read failure
model load/unload
model inference failure
zone file load/save
traffic decision errors
dataset save/export errors
```

Do not log these:

```text
passwords
Wi-Fi credentials
private API keys
unnecessary personal data
large full image frames
large model arrays
```

## 6. Debugging workflow

When a bug appears:

```text
1. Identify page/API/module.
2. Check browser console.
3. Check backend logs.
4. Search error code in docs/ERROR_CODES.md.
5. Reproduce with mock/fake data.
6. Fix the smallest module.
7. Add/update logs if the failure was hard to diagnose.
8. Update patch notes.
```

## 7. Mock-first rule

For GUI and API development, use mock data first.

Do not debug UI layout, threshold sliders, detection tables, or traffic-light state using a live camera or real AI model unless necessary.
