# Patch 0_5_24 — Independent per-camera freshness

Candidate `0_5_24`, previous `0_5_23`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Harden existing per-source background inference: discard repeated or out-of-order camera samples independently, allow frame-number resets only with newer timestamps, and prevent detection-cache reuse across reconnects. Existing simulation/real frame routing and selected-source traffic state remain distinct.

Existing `MultiCameraInferenceService` remains the source of independently inferred frames for saved physical/simulation cameras. It is not a new real-world distributed traffic controller; configured topology is not measured vehicle transfer. Test source ordering and inference caching plus existing camera, Crosswalk and signal safety tests. Local Windows/ESP performance and owner PASS pending.
