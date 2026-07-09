# PC Studio App Template — 0_0_4

This patch creates the first structured template of the **PC Studio App**. It is not the final app and does not implement real AI, real camera input, training, or traffic control.

The purpose of this version is to confirm:

```text
1. Which pages the PC app needs.
2. Which functions each page should contain.
3. How the GUI should be laid out.
4. Where future code modules and API routes should live.
```

## Design rule

The PC app must stay modular:

```text
large page
→ small page file
→ small reusable component
→ API wrapper
→ backend route
→ service function
→ shared schema/error code
```

Avoid adding large all-in-one files.

## Current frontend template pages

```text
Dashboard
Live AI View
Camera Sources
Zone Editor
Traffic Logic
Dataset Capture
Dataset Review
Train / Export
Model Registry
Settings
Logs & Errors
```

## Current backend placeholder route groups

```text
/api/camera
/api/inference
/api/zones
/api/traffic
/api/dataset
/api/training
/api/models
/api/settings
/api/logs
/api/template
```

Each route group currently returns placeholder/template information. Future patches should implement them one function at a time.

## What to check manually

After uploading this patch, open the frontend and check:

```text
- Is the sidebar page list correct?
- Are any pages missing?
- Are any page names unclear?
- Is the Live AI page layout suitable?
- Should Dataset Capture and Dataset Review be separate?
- Should Train and Export be separate later?
- Is the Logs & Errors page enough for debugging?
```

Do not implement real model inference until the app structure is accepted.
