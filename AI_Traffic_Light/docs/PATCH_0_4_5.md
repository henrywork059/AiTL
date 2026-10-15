# Patch 0_4_5 — Mint theme and selected-state indicators

Candidate: `0_4_5`; previous candidate: `0_4_4`; owner-accepted stable baseline: `0_4_0`.

Owner-selected dark primary `#57FFED` is used for primary actions, navigation, selected views, focus and active controls. Light mode uses contrast-safe `#006F66` with the same teal identity. Success/warning/error continue to represent operational status only.

A visible dot, selection bar or border accompanies selected navigation, tab, list, segmented and pressed controls. This includes Camera Settings status, Crosswalks, Junction Network edge selections, Simulation Experiments, Signal Control, Traffic Analytics, Dataset Review and Live AI checked filters. Existing state logic is reused; no backend or traffic controller changes.

Static design checks include primary text contrast (light/dark) and source-level selected-state indicators. Windows frontend build, UI screenshots and runtime acceptance remain pending. Use the established one-line updater.
