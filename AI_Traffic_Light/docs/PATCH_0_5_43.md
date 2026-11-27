# Patch 0_5_43 — Bounded HTTP upload aggregation integrity

Candidate `0_5_43`, previous `0_5_42`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

During the V0540 camera upload fix, the route was updated to stream and enforce an 8 MiB limit but still retained every received network chunk in a Python list before joining the complete frame. A highly fragmented upload therefore incurs unnecessary Python object/list memory overhead, despite byte-size enforcement.

Keep the existing route and strict `store_upload(validate_decode=True)` call. Accumulate the accepted chunks directly in one `bytearray`, compute the next body size before each append, and convert to bytes only once when passing to the existing frame service. Preserve the exact 413 code/details, boundary semantics, MIME handling, request ID, camera service and ESP TCP fast path.

Regression: extend `test_v0540_camera_upload_stream_limit.py` with 4,098 chunks to verify exact bytes and empty chunk handling; retain exact-boundary and early-abort scenarios. Execute V0541 integrity, remote TCP tests, structure guard, full offline suite and frontend typecheck/build. Windows owner command: `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. CI PASS is not owner PASS.
