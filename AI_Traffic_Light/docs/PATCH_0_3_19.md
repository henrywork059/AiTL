# PATCH_0_3_19 — Compact Camera Settings and all-camera status

Version: `0_3_19`  
Previous candidate: `0_3_18`  
Passed baseline: `0_3_11` (unchanged, pending owner PASS)

## Scope

- Keep all saved camera connection states visible in an auto-updating, color-coded strip; clearly distinguish physical stream connected from requested/reconnecting.
- Collapse IP manager, image/FPS controls and detailed diagnostics independently, while leaving the selected camera dropdown and streaming buttons visible.
- Remove deprecated V037/compatibility prose and avoid displaying redundant camera function checklist on the Settings page.
- Reuse the shared status poll and existing camera profiles/session/backend/MJPEG contract. No firmware, dependency, new API or inference architecture changes.

## Validation

- Static regression: `python scripts/test_camera_settings_page_structure.py`; existing serial polling and structure checks.
- Owner runs Windows `scripts/update_test_run.ps1`, checks live ESP status transitions, preview selection and saved settings before acceptance.
