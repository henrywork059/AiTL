# Patch 0_1_0 — Test-Ready Mock PC Studio

## Purpose

This patch changes the project from a layout-only PC Studio template into a locally smoke-testable mock app.

## Main changes

```text
- backend smoke-test endpoint
- frontend backend-status display
- mock API refresh flow
- visible smoke-test checklist in Dashboard
- mock logs display
- settings page showing API base/backend status
- Windows start scripts for backend and frontend
- backend smoke-test script
- local testing documentation
```

## Still not implemented

```text
- real camera capture
- ESP-CAM stream
- YOLO inference
- segmentation
- training
- model export
- physical traffic-light control
```

## Suggested commit message

```text
Patch v0_1_0: add test-ready mock PC Studio
```

## Upload note

This patch contains only changed/new files. Upload the changed files into the existing `AI_Traffic_Light/` folder in GitHub and allow GitHub to replace matching files.
