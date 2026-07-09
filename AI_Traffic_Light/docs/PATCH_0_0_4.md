# Patch 0_0_4 — PC Studio App Template

## Purpose

This patch adds the first structured template for the main PC app.

It is designed to confirm:

```text
- page list
- function list
- GUI layout
- backend API grouping
- frontend component structure
```

It does **not** implement real AI inference, training, camera capture, ESP-CAM streaming, or traffic-light control.

## Files changed/added

Main frontend additions:

```text
apps/pc-studio/frontend/src/App.tsx
apps/pc-studio/frontend/src/layout/AppShell.tsx
apps/pc-studio/frontend/src/pages/*.tsx
apps/pc-studio/frontend/src/components/PlaceholderPanel.tsx
apps/pc-studio/frontend/src/components/FunctionChecklist.tsx
apps/pc-studio/frontend/src/components/MetricStrip.tsx
apps/pc-studio/frontend/src/components/AppStatusBar.tsx
apps/pc-studio/frontend/src/constants/appNavigation.ts
apps/pc-studio/frontend/src/constants/functionRegistry.ts
apps/pc-studio/frontend/src/types/app.ts
apps/pc-studio/frontend/src/styles.css
```

Main backend additions:

```text
apps/pc-studio/backend/app/routes/camera.py
apps/pc-studio/backend/app/routes/inference.py
apps/pc-studio/backend/app/routes/zones.py
apps/pc-studio/backend/app/routes/dataset.py
apps/pc-studio/backend/app/routes/training.py
apps/pc-studio/backend/app/routes/models.py
apps/pc-studio/backend/app/routes/settings.py
apps/pc-studio/backend/app/routes/logs.py
apps/pc-studio/backend/app/routes/template.py
apps/pc-studio/backend/app/services/template_state.py
```

Main docs:

```text
docs/PC_STUDIO_TEMPLATE.md
docs/PC_STUDIO_FUNCTION_LIST.md
docs/PC_STUDIO_GUI_LAYOUT.md
```

## Human check after upload

Open the frontend and confirm:

```text
- sidebar page list
- page grouping
- Live AI layout
- whether Capture/Review should stay separate
- whether Train/Export should stay together
- whether Logs & Errors is enough for debugging
```

## Suggested commit message

```text
Patch v0_0_4: add PC Studio app template
```
