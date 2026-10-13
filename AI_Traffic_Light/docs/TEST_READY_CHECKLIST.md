# V0323 Test-Ready Checklist

```text
version: 0_3_23
previous_version: 0_3_22
passed_baseline: 0_3_11
status: Crosswalk regions and shared simulation candidate
```

- [ ] Multiple crosswalks and their independent region sets persist across restart.
- [ ] Edit regions opens a wide independent workspace without crowding Crosswalks page.
- [ ] Each Add region creates a quadrilateral; four drag handles work; label edits, deletion, selection work.
- [ ] Side A and Side B show identical region geometry on the selected physical preview, with no false claim of camera calibration.
- [ ] Old crosswalk JSON without regions is loaded and normalized.
- [ ] Invalid/self-crossing/out-of-bounds regions rejected without damaging saved data.
- [ ] Junction Network and Crosswalks share the same simulation on/off state as Camera Sources; exactly one simulated feed.
- [ ] Physical preview cannot show a different active ESP as the chosen camera; simulation pauses/resumes physical input safely.
- [ ] Focused service/structure regressions, project structure, frontend typecheck/build and Windows live smoke pass.
- [ ] Owner confirms PASS; `0_3_11` remains passed baseline until then.
