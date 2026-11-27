# Patch 0_5_42 — Separate HTTP upload integrity from ESP TCP performance

Candidate `0_5_42`, previous `0_5_41`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

**CI evidence:** V0541 offline regressions failed twice in `test_remote_camera_pull.py`: the shared service began fully decoding all frames, including header-only mock JPEG packets delivered by the ESP TCP stream. The issue is not a 0.5-second startup timeout; a supposedly lightweight transport path was forced through a new heavyweight image decoder. Real ESP frames would also incur unnecessary decode cost.

**Correction:** Restore `_image_dimensions` as the shared type/header parser. Move full OpenCV decodability checking into a separate service helper, called only when `validate_decode=True`. The legacy HTTP `/api/camera/frame` route supplies this flag, while existing TCP service calls retain the default header-only behavior. Keep the 16,777,216-pixel protection and rejection-without-state-change for strict HTTP uploads. Do not change ESP transport data, physical output, signal controls or 3D simulation.

**Tests:** V0540 asserts the route explicitly requests full validation. V0541 checks valid/invalid MIME, truncated images, state preservation, pre-decode pixel cap and absence of redundant decoding in the fast path. Run `test_remote_camera_pull.py`, `test_remote_camera_session.py`, structure, full offline suite, typecheck/build and Windows `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. Owner Windows/ESP PASS pending.
