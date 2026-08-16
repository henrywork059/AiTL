# PC Studio GUI Layout — V023 candidate

The established sidebar + page-content layout is retained. V023 expands the existing **Traffic Logic** page instead of adding another top-level page.

## Traffic Logic tabs

### Live Decision
- active simulated phase/countdown and next phase;
- base vs effective phase duration;
- operating mode/profile, pending request and data freshness;
- active rule count plus priority-ordered active/suppressed/inactive/unavailable explanations;
- current pedestrian/vehicle demand, tracking context, decision-zone and per-region counts.

### Normal Timing
- editable min/base/max timing for vehicle green, yellow, all-red-to-pedestrian, pedestrian WALK, pedestrian CLEAR, and all-red-to-vehicle;
- maximum cycle duration, stale-observation timeout and short-term demand-memory window;
- Save / Discard / Reset Defaults apply to persistent signal policy.

### Adaptive Rules
- one card/row per structured rule;
- enable/disable, threshold, stable-for/persistence, adjustment, cooldown and priority controls;
- rule trigger/action/target phase remain visible so users can reason about arbitration.

### Safety & Test
- protected transition/minimum-service/fallback explanations;
- explicit Test-mode manual pedestrian/vehicle counts;
- mobility/accessibility and fallen-person incident inputs clearly marked as manual test sources;
- Apply Test Inputs, Clear Incident and Reset Adaptive State;
- non-mutating scenario preview buttons for vehicle queue, pedestrian demand/wait, slow crossing, mobility assistance and incident cases.

### Decision History
- runtime phase/rule/config/reset/incident audit events;
- explicit history clear action;
- identifies `outputs/signal_rules/decision_history.jsonl` as runtime data.

## Existing V022 surfaces

Live AI keeps trained-model/track/zone overlays and the compact simulation signal. Zone Editor retains polygons plus two-point counting lines. Traffic Analytics retains separate Occupancy and Flow / Tracks modes.

## Safety presentation

All signal timing/rule controls are described as simulator policy. No page implies direct physical/public-road traffic-light control. Mobility/fall conditions are not shown as live detections unless a compatible future perception source actually provides them.

## Shared visual system

The frontend visual language is now defined separately in `docs/PC_STUDIO_DESIGN_SYSTEM.md` and implemented through `src/styles/` design tokens/base/layout/components. The GUI layout document remains responsible for page structure and control placement.

V023 uses a restrained dark operations/workbench presentation: solid graphite layers, compact 4–8px radii, low elevation, desaturated semantic colors, no decorative full-page gradient/glass treatment, and no generic purple/neon “AI” accent. Page-specific styles should consume the shared tokens instead of introducing private palettes.
## Shared visual hierarchy

PC Studio uses the shared design system in `docs/PC_STUDIO_DESIGN_SYSTEM.md`. The shell follows the operating-system light/dark preference and uses neutral base/elevated surfaces, compact radii, restrained borders, native system typography, and one muted steel-blue interaction family. Semantic green/amber/red is reserved for real state meaning and the simulated signal; page-specific styling must consume shared role tokens.

The page header uses a subtle separator so page identity remains visually above panel content. Sidebar selection and Traffic Logic tabs use restrained accent edges/underlines rather than saturated filled cards. Camera/detection overlays retain dedicated high-contrast visualization colors so they remain readable over imagery in either application appearance.

