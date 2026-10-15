# Patch 0_4_16 — Regions terminology, remove empty Traffic Zones page

**Candidate:** `0_4_16` · **Previous candidate:** `0_4_15` · **Accepted baseline:** `0_4_14`.

## Changes

- Remove the empty `ZonesPage.tsx` and its `zones` page ID/navigation/route. Do not alter working Crosswalks or Region Editor workflows.
- Rename all user-facing `Zone/Zones` UI terminology to `Region/Regions` in Live AI overlays/toggle, Signal Control observation/condition labels, Analytics status/notes, mock labels, feature registry and the hidden editor's display strings.
- Keep internal `Zone` types, `zone_id`, `zone_class_count`, `zones` array, `/api/zones`, saved ID prefixes, CSS class names and legacy `zone_editor` route. Renaming serialized keys would corrupt existing configs and API consumers; no migration is requested.
- Update historic navigation regression and add `test_v0416_region_terminology.py` to protect deleted navigation and the compatibility contract.

## Validation

Run the single-command updater on Windows for Python regressions, frontend typecheck/build, backend smoke and launch. Actual Windows UI acceptance remains pending and V0416 is a candidate until owner PASS.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
