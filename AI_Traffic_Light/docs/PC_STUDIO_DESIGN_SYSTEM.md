# PC Studio Design System — V024 candidate

This is the authoritative presentation and interface-copy reference for PC Studio. Page/layout documents define information architecture; this document defines visual roles, color semantics, hierarchy, controls, states, and writing style.

## Design intent

PC Studio is a desktop engineering workbench for a local traffic-simulation and computer-vision prototype. It should look deliberate, quiet, and operational—not like a promotional AI dashboard. Information should be scannable before it is decorative.

## Reference basis

The V024 refinement applies the role model in **Material Design 2 — The color system**:

- primary color identifies the application and the most important actions;
- secondary color is selective and supports secondary emphasis;
- background and surface roles carry most application area;
- error is a semantic role, not a brand color;
- readable foreground roles are defined for colored surfaces (the Material “on” concept);
- color hierarchy must preserve legibility and should not be the only state cue.

The existing dark appearance also retains the Material dark-theme surface model: `#121212` at the base, with progressively lighter neutral elevated surfaces.

Supporting references used earlier in this design system remain Apple HIG, Figma color theory, and UX Pilot color-theory guidance. AiTL uses those references as design rationale; it does not copy their component libraries or product branding.

## Color-role model

Most of the interface remains neutral. Color has a job.

### Primary

Primary identifies navigation, links, focus, and the dominant action in a workflow.

Light appearance:

| Role | Value |
| --- | --- |
| Primary | `#315F9E` |
| Primary hover | `#274F85` |
| Primary active | `#1F426F` |
| Primary surface | `#E8EEF7` |
| On primary | `#FFFFFF` |

Dark appearance:

| Role | Value |
| --- | --- |
| Primary | `#90CAF9` |
| Primary hover | `#BBDEFB` |
| Primary active | `#64B5F6` |
| Primary surface | `rgba(144, 202, 249, 0.12)` |
| On primary | `#0D1B2A` |

Use primary for:

- active navigation;
- the main action in a panel, such as **Save**, **Start**, **Refresh**, or **Apply**;
- focus indication and links;
- informational emphasis where a brand/interaction role is appropriate.

Do not use primary merely to make a panel more interesting.

### Secondary

Secondary is deliberately sparse. It distinguishes selected/active secondary controls and continuous progress without competing with the main action.

Light: `#00796B` with `#FFFFFF` on-secondary.
Dark: `#80CBC4` with `#102522` on-secondary.

Use secondary for:

- checkbox/radio/range accent;
- progress bars;
- selected secondary states;
- current-observation or active-rule emphasis where “success” would be misleading.

Do not use secondary as a second general brand color across large surfaces.

### Neutral surfaces

Background, shell, panel, field, and raised-control colors are neutral. They carry almost all screen area.

Light appearance uses a cool-neutral canvas (`#F5F6F8`) and white/elevated surfaces. Dark appearance retains:

| Elevation role | Surface |
| --- | --- |
| 0dp canvas/shell | `#121212` |
| 1dp normal panel | `#1E1E1E` |
| 2dp raised control | `#232323` |
| 4dp hover | `#272727` |
| 8dp pressed/overlay | `#2E2E2E` |

Dark depth comes primarily from controlled luminance differences rather than glow or large shadows.

### Semantic colors

Semantic colors communicate outcomes only:

- success/healthy/confirmed: green;
- warning/pending/fallback/unsaved: amber;
- error/destructive: red;
- neutral metadata/counts/context: neutral;
- informational emphasis: primary/info role.

A generic `.status-pill` is neutral. It must never default to green. Green is only applied by an explicit success/implemented state.

Traffic-light red/amber/green remain separate scene tokens because they encode the simulated signal, not application health.

## “On” colors and contrast

Every saturated primary/secondary/error surface must use a corresponding readable foreground. Do not assume ordinary body text will remain readable when moved onto a colored background.

Normal text targets WCAG AA contrast (at least 4.5:1). Color is never the only signal: text labels, state names, borders, and explanations remain visible.

## Presentation hierarchy

1. **Page title** — identifies the work area.
2. **One-sentence page description** — describes current purpose, not release history.
3. **Panel title** — names one task or data group.
4. **Primary action** — one dominant action per immediate workflow where practical.
5. **Secondary controls** — neutral or secondary-role styling.
6. **Status** — semantic only when the status has semantic meaning.

Panels remain neutral and compact. Avoid gradients, glass effects, neon glows, decorative purple/cyan AI styling, excessive pills, and unnecessary large-radius cards.

## Control hierarchy

- Default button: neutral action.
- `.primary`: dominant workflow action.
- `.secondary`: secondary emphasis/selective action.
- `.danger`: destructive action and explicit destructive confirmation context.
- Disabled controls reduce emphasis but remain readable.
- `:focus-visible` must remain clearly visible in light and dark modes.

Do not make every button primary. A panel with three equally saturated buttons has no hierarchy.

## Status hierarchy

Use status styling according to meaning:

| Meaning | Treatment |
| --- | --- |
| Neutral metadata, count, local/runtime context | neutral pill |
| Current selection/observation emphasis | secondary/info pill |
| Healthy, available, completed | success pill |
| Pending, fallback, stale, unsaved | warning pill |
| Failed/error | error pill |

A status word should be understandable without its color.

## Interface writing standard

V024 removes much of the historical/placeholder wording from the working UI. Visible product copy should follow these rules:

1. **Describe the current task, not development history.** Avoid “V021/V022/V023” in normal page descriptions unless version history is genuinely the subject.
2. **Lead with user meaning.** “Traffic measurements” is preferable to “Compare V021 sampled occupancy with V022…”
3. **Use sentence case.** Reserve ALL CAPS for real identifiers/log levels.
4. **Buttons use concise verbs.** Examples: `Refresh status`, `Save policy`, `Capture frame`, `Build dataset`, `Start training`.
5. **Destructive actions name what is deleted.** Confirmation text states the affected files/state and whether the action is permanent.
6. **Status text reports outcome/state.** Prefer `model running`, `rebuild required`, `observations current`, `fallback timing` over vague labels.
7. **Explain technical distinctions where users can act on them.** Occupancy versus flow, active versus default model, and fixed versus adaptive timing should be stated near the relevant controls.
8. **Remove obsolete setup language once a surface is working.** Do not show phrases such as “Confirm layout first” on test-ready working pages.
9. **Keep the safety boundary precise, not noisy.** The app must clearly state that signal outputs are simulation-only and not connected to physical/public-road infrastructure, but this does not require repeating a long disclaimer in every card.
10. **Do not overclaim perception.** Mobility assistance and fallen-person conditions remain explicit test inputs unless a compatible detector is actually implemented.

## Source ownership

```text
src/styles.css                 stable shared CSS entrypoint
src/styles/tokens.css          color/spacing/type/elevation roles
src/styles/base.css            document, controls, action hierarchy, focus
src/styles/layout.css          shell and layout grids
src/styles/components.css      reusable panels/status/forms/tables/overlays
src/pages/*.css                page-specific layout only
```

Page CSS consumes shared tokens and must not create independent palettes.

## System adaptation and accessibility

- Follow `prefers-color-scheme` for light/dark appearance.
- Follow `prefers-contrast: more` where available.
- Follow `prefers-reduced-motion: reduce`.
- Preserve Windows/browser forced-color behavior.
- Never lower normal-text contrast just to make the interface look softer.
- Do not rely on red/green distinction alone.

## Review checklist for future patches

Before adding or changing UI:

- Is there exactly one clear primary action for the immediate task?
- Is secondary color used selectively rather than decoratively?
- Are neutral badges neutral?
- Are success/warning/error colors semantically accurate?
- Does every colored surface have a readable foreground?
- Does the copy describe the current capability instead of its development history?
- Are destructive effects explicit?
- Are light and dark appearances both usable?
- Does the page remain clearly a simulation/engineering tool rather than a promotional AI dashboard?
