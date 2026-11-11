# Patch 0_5_41 — Decodable camera uploads and pixel memory safety

Candidate `0_5_41`, previous `0_5_40`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

**Audit finding:** `CameraFrameService.store_upload` previously accepted image dimensions taken only from PNG IHDR or JPEG SOF markers. An incomplete or corrupted upload could therefore become the newest frame, even though downstream OpenCV processing could not decode it. A tiny compressed image could also declare huge dimensions and trigger a costly decoder allocation if full decoding were added without a pixel bound.

**Correction:** Keep the existing lightweight PNG/JPEG signature and dimension parsers to reject invalid MIME and guard maximum pixel count before allocation. Then decode with the existing OpenCV dependency outside the frame-state lock, require decoded dimensions to match the header, and reject failures through the existing 422 `CAMERA_FRAME_INVALID`. No new decoder, API endpoint or heavy dependency is added. The 8 MiB bounded streaming fix from V0540 remains intact.

**Verification:** `python scripts/test_v0541_camera_upload_integrity.py` covers valid PNG/JPEG, truncated PNG/JPEG, MIME mismatch, oversized declared pixel count without decode, last-valid-frame preservation and counter stability. Run `test_v0540_camera_upload_stream_limit.py`, camera service/API regressions, structure/offline suite, frontend typecheck/build and Windows `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. CI success does not imply owner PASS.
