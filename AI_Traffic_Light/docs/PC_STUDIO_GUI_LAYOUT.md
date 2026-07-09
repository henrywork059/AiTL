# PC Studio GUI Layout — Draft 0_0_4

This document describes the planned layout of the PC Studio App.

## Global layout

```text
┌─────────────────────┬────────────────────────────────────────────┐
│ Sidebar navigation  │ Page header                                 │
│                     ├────────────────────────────────────────────┤
│ Operate             │ Main page content                           │
│ - Dashboard         │                                            │
│ - Live AI           │                                            │
│ - Cameras           │                                            │
│                     │                                            │
│ Traffic setup       │                                            │
│ - Zones             │                                            │
│ - Logic             │                                            │
│                     │                                            │
│ Data & model        │                                            │
│ - Capture           │                                            │
│ - Review            │                                            │
│ - Train             │                                            │
│ - Models            │                                            │
│                     │                                            │
│ System              │                                            │
│ - Settings          │                                            │
│ - Logs              │                                            │
└─────────────────────┴────────────────────────────────────────────┘
```

## Live AI page layout

```text
┌──────────────────────────────────────┬──────────────────────────┐
│ Camera / detection canvas            │ Signal simulator          │
│ - frame preview                      │ Traffic state metrics     │
│ - boxes                              │ Controls                  │
│ - zones                              │ Zone list                 │
├──────────────────────────────────────┴──────────────────────────┤
│ Detection result table                                           │
└──────────────────────────────────────────────────────────────────┘
```

## Dataset pages

Dataset Capture and Dataset Review are separate on purpose:

```text
Dataset Capture = collect data quickly while viewing camera/model output.
Dataset Review  = inspect, filter, and prepare saved data for training.
```

They can be merged later if they feel too small.

## Train / Export page

Training and export are together in 0_0_4 because training is not implemented yet. Later, they may be split into:

```text
Train
Evaluate
Export
```

## Logs page

The Logs & Errors page should eventually show:

```text
- timestamp
- scope/module
- error code
- message
- request ID
- related page/function
- suggested fix
```

This is important because the project will be developed with small modules and frequent patches.
