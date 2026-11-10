# Patch 0_5_29 — Bounded HTTP camera uploads

Candidate `0_5_29`, previous `0_5_28`, accepted baseline `0_5_0`, development branch `main`.

`POST /api/camera/frame` previously buffered the complete request with `request.body()`, then called the existing `CameraFrameService.store_upload()` 8 MiB check. A very large request could occupy unbounded memory before returning HTTP 413. The route now reads stream chunks, accumulates at most 8 MiB, rejects the first oversized chunk with the existing `CAMERA_FRAME_TOO_LARGE` error code, and delegates accepted bytes to the unchanged image validator. The response envelope and request-ID handling are preserved.

Validation: `python scripts/test_v0529_camera_upload_stream_limit.py`, existing camera-frame and simulation API scripts, structure checks and full Windows GitHub Actions CI. Physical ESP and local Windows testing are separate owner checks. No network signal changes or physical signal actuation.
