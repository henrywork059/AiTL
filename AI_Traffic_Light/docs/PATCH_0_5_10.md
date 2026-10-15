# Patch 0_5_10 — Network signals, timing and adjustment templates (partial)

**Candidate:** `0_5_10`; **previous:** `0_5_9`; **owner-accepted baseline:** `0_5_0`.

## Implementation

- Traffic navigation adds **Traffic Light Settings** and **Live Signal Adjustments** without removing the existing advanced Signal Control page.
- Timing page saves default signal phase seconds to the active existing profile through `PUT /api/traffic/signal-rules`, preserving protected minimums, max and all-red clearance.
- Adjustment page offers disabled-by-default templates for class-based emergency requests, emergency vehicle green extensions, vehicle/pedestrian queues, wheelchair-class extensions, and near-end pedestrian clearance. The templates reuse existing ranked signal scenarios; missing class/legacy active-zone observations do not authorize action.
- Backend adds `phase_remaining_seconds` to scenario metric evaluation; near-end clearance can combine `pedestrians_crossing` with an end-of-phase threshold. Existing safety caps and sequential safe transitions remain authoritative.
- Network cards show small red/amber/green vehicle and pedestrian STOP/WALK/CLEAR lights and countdown from the **shared simulation signal status only for its matching observed source**; other boxes are marked unverified. Adjacent connected crossings show **advisory-only** notices when a rule is active, explicitly not an applied signal change. Dragging, network save, camera and controller logic otherwise retained.

## Not yet implemented

- Crosswalk-specific independent signal state machines and phases.
- Explicit per-edge movement conflict topology and coordinated arbitration to actually change a directly connected neighbour's signal.
- Physical ESP signal control, emergency identity verification, flashing-green public-road commands, or independent live phase data for all crossings.
- Guaranteed emergency / wheelchair detector output or automatic Crosswalk region to legacy active signal-zone mapping.

## Validation and acceptance

Added `scripts/test_v0510_signal_adjustments.py` and `scripts/test_v0510_signal_navigation.py`. Focused static cross-file checks only can be performed via GitHub tooling; local Python, TypeScript/Vite, live smoke and Windows hardware tests are pending. Run the full Windows runner and manually verify both new pages, Network signal provenance and protected signal transitions. **No PASS claimed**. Baseline remains `0_5_0`.
