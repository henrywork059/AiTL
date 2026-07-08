# Shared Schemas

This folder stores shared data definitions for the PC Studio App, frontend GUI, backend, and future device integrations.

Keep these formats stable:

- detection-frame.schema.json
- zones.schema.json
- traffic-state.schema.json
- classes.default.json

Important rule:

```text
Store detection boxes in original image coordinates.
```

Do not store boxes in displayed screen coordinates.
