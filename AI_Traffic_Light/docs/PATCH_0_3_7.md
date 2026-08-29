# Patch 0_3_7 — Adaptive single-window low-latency ESP streaming

V037 / `0_3_7` is a new candidate explicitly requested by the owner after V036. `passed_baseline` remains `0_2_4`.

## Why V037 exists

Physical V036 R6 testing proved the persistent TCP path could stay connected and complete frames, but typical JPEGs around 11–22 KB still produced 100–500+ ms sends and occasional timeout/reconnects. The physical logs repeatedly showed partial writes near the classic ESP32 lwIP TCP send-buffer boundary.

## V037 R2 changes

- Keep the V036 `aitl-tcp-jpeg-v1` frame format, PC-initiated session model and multi-ESP architecture.
- Firmware identity is `aitl-camera-v037`; PC Studio accepts V037 and V036 binary-TCP nodes during migration.
- New camera defaults remain QVGA / JPEG 24 / 15 FPS. Existing saved profiles are not rewritten.
- Adaptive JPEG compression now targets a ~5000-byte payload, intentionally below the common ~5744-byte classic ESP32 lwIP default send buffer.
- Oversized captured JPEGs are **not** sent as partial ATL1 frames while compression can still be increased. They are dropped locally, compression is tightened aggressively, and a fresh replacement frame is captured a few milliseconds later. This avoids a reconnect just to learn that an oversized frame cannot queue promptly.
- If a real partial TCP send still occurs, V037 learns a more conservative payload target from the number of bytes accepted before the stall.
- Compression steps scale with how far the JPEG exceeds the current payload target instead of always increasing by a fixed small amount.
- Maximum adaptive JPEG quality number is 50; the user's configured value remains the best-quality recovery floor.
- Quality recovery is deliberately slower and requires substantial payload headroom.
- PC Studio increases the TCP receive buffer request to 256 KiB.
- ESP telemetry adds `adaptive_payload_target_bytes`, `adaptive_local_frame_drops` and `adaptive_window_learns` alongside configured/effective JPEG quality and send EWMA.
- Camera Sources displays these transport diagnostics.


## V037 R3 updater/worktree repair

- Removed the automatic V036 metadata-finalizer call from `scripts/update_test_run.ps1`. Candidate metadata must already be committed on GitHub/main (or deliberately overlaid locally); the test runner no longer edits tracked release files.
- Kept the strict pre-pull dirty-tree safety check for genuine tracked edits. Runtime/untracked files remain allowed and are never cleaned destructively.
- Added a second tracked-cleanliness assertion after the non-live validation suite so a future test/helper that modifies tracked source fails immediately in that same run rather than breaking the next update.
- Extended `test_update_test_run_script.py` to reject reintroduction of the historical finalizer or tracked-file write operations.
- This is a same-candidate V037 repair. Camera transport, adaptive JPEG behavior, APIs and firmware are unchanged from R2.

## Deliberate non-changes

- No UDP transport in V037 R2. This revision first attacks the specific TCP send-window behavior demonstrated by the V036 physical logs.
- No ESP-side AI/inference.
- No public-road or physical signal authority.
- No rewrite of `config/remote_cameras.json`.
- The 16-byte `ATL1` header and JPEG payload format are unchanged.

## Acceptance target

At 320 × 240 / saved JPEG 24 / 15 FPS, the ESP should converge quickly toward JPEG payloads near or below the adaptive target. After convergence, successful send times should fall substantially and reconnect/failure counters should stop climbing continuously. Image quality must remain adequate for the project's local detector. Physical results decide acceptance.
