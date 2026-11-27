# Patch 0_5_34 — More volumetric synthetic agents and seamless reentry

Candidate \`0_5_34\`, previous \`0_5_33\`, accepted baseline \`0_5_0\`, branch \`feature/interactive-3d-simulation\`.

Keep the existing read-only CSS 3D world. Add raised car roofs, four body sides and wheels, with upright pedestrian head/torso/arms/legs using `preserve-3d`. Do not add a parent filter that flattens these models.

The simulator reuses vehicle IDs after off-screen respawn; the old 430 ms position tween displayed this as a backward jump across the road. Compare the previous and current canonical X positions and suppress interpolation only for a large reset; keep smooth motion between normal snapshots. Do not change backend agent creation, signal timing, camera/AI contracts, hardware, captures or image-coordinate editing.

Validate with `python scripts/test_v0515_3d_simulation.py` (including six Node reentry cases), structure/offline regressions, frontend typecheck/build and Windows `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. Inspect four camera views and controls, detect no backwards jumps, and confirm physical camera and editor behavior remain unchanged. CI PASS is not owner PASS.
