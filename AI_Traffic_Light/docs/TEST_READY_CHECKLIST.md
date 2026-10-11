# V0319 Test-Ready Checklist

```text
version: 0_3_19
previous_version: 0_3_18
passed_baseline: 0_3_11
status: Collapsible camera settings and status candidate
```

## Camera Settings UI

- [ ] Always-visible saved-camera status strip shows every profile, selected-preview identification and color-coded Streaming / Connected / Reconnecting / Paused / Unreachable / Saved states.
- [ ] Strip updates from existing non-overlapping polling and does not overwrite pending form edits.
- [ ] Dropdown and Start/Stop controls remain visible while IP manager, camera settings and detailed diagnostics collapse independently.
- [ ] Saved-camera management and image/FPS controls still persist and apply; errors and backend warnings are not hidden.
- [ ] Deprecated V037 prose/compatibility text is absent.
- [ ] Simulation never appears as physical preview, and other streams remain active during selection.

## Validation

- [ ] `python scripts/check_structure.py` passes.
- [ ] `python scripts/test_camera_settings_page_structure.py` passes.
- [ ] `python scripts/test_frontend_polling_structure.py` passes.
- [ ] Frontend `npm run typecheck` and `npm run build` pass.
- [ ] Full Windows `update_test_run.ps1` and real ESP test pass.
- [ ] Owner confirms PASS; `0_3_11` remains the passed baseline until then.
