# Patch 0_5_47 — Preserve ESP cached-frame identity

Candidate `0_5_47`, previous `0_5_46`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap [Update 03 / H03](ROADMAP.md#4a-numbered-update-by-update-implementation-queue).

## Root cause

Promotion re-uploaded cached JPEG bytes, resetting their PC receive timestamp and allocating a new shared frame number. Background inference separately used the ESP sequence number for the same image, so the two consumers disagreed on identity.

## Change

Cache one validated immutable CameraFrame per accepted ESP packet, with its original PC receive timestamp and a globally allocated frame ID. Selection, simulation return and background inference reuse the same object; stale caches remain rejected. Ordinary HTTP uploads still allocate and publish new frames. ESP wire sequence remains a transport diagnostic, not the application frame ID.

Frame IDs are unique within the backend process and can be non-monotonic in the selected view when switching cameras; they identify observations rather than selection events. No new API fields, settings, firmware or traffic-signal behavior. This does not deduplicate independently received wire packets or fix downstream source-switch tracking or disconnected cache invalidation (Update 04).

## Validation

Reproduced against the original hash-matched promotion method with an injected receiver: original timestamp 1000 became 1100 and two promotions allocated IDs 1 and 2. Patched isolated method execution passed 9/9 behavioral checks using three FNV-1a-matched source blocks (camera upload methods ca8e8669, manager ingest/promotion 29058cfc, inference snapshot a7bfb222), injected dependencies and real JPEG fixtures: background isolation, preserved time/ID, A/B/A replay, distinct same-ms packets, stale rejection, simulation ownership transition, ordinary upload, retired generation and invalid image rejection. This is not full-module regression execution; image validation and simulation were injected. Direct clone failed DNS resolution; repository regression, full CI and owner Windows/ESP validation pending.

Focused checks: `scripts/test_v0547_cached_frame_identity.py` and updated `scripts/test_remote_camera_multi.py` (publication race fixture now intercepts immutable-frame promotion). Verify V0544–V0546 and full runner before owner PASS. Next: Update 04, invalidate disconnected camera observations.
