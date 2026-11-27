# Patch 0_5_48 — Invalidate disconnected camera observations

Candidate `0_5_48`, previous `0_5_47`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap Update 04 / H03.

## Root cause

Explicit stop/disconnect/restart kept receiver and manager caches. Inference only checked image age and could return completed predictions from a retired camera. Mode round trips could retain pre-transition predictions.

## Change

Retire camera delivery before explicit stop, disconnect, reconnect, restart or session replacement. Clear only that source's latest image and increment its observation epoch. Background inference snapshots carry source/mode tokens; invalid or expired predictions are suppressed at completion, API read and virtual-observation forwarding. A mode-generation change invalidates pre-transition predictions, while fresh cached images may still be promoted with their original identity.

No firmware, TCP wire, public API schema or signal policy changes. Unexpected Wi-Fi/transport loss still expires by the existing five-second freshness bound; explicitly stopped sessions are invalidated immediately. The inference snapshot is checked before forwarding but not transactionally coupled to controller ingestion; already-forwarded virtual observations follow existing controller freshness/fallback policy. Concurrent user control actions are not fully serialized by this change.

## Evidence

Executed isolated Python reproduction using the retrieved original stop/disconnect and inference-snapshot methods: both operations left the cached image available (2/2 defects reproduced). Patched isolated execution passed 9/9 behavioral checks: stop/neighbour isolation, stale API result suppression, stopped callback, cancelled worker after restart, new delivery and slow current observation, simulation round trip, disconnect, old device generation, and inference completion/virtual snapshot filtering. All 12 copied patched method bodies matched staged source by FNV-1a checksum. Camera/session/clock/model/controller dependencies were injected; this is not a full-module test. Direct GitHub clone failed DNS resolution. Repository regressions added; full CI and owner Windows/ESP acceptance pending.

Run `scripts/test_v0548_observation_invalidation.py`, `scripts/test_remote_camera_multi.py`, `scripts/test_v0527_late_inference_shutdown.py`, V0544–V0547 and the complete runner before owner PASS. Next: Update 05 / H04, reproducible test execution.
