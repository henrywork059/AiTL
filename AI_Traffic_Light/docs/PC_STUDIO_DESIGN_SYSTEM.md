# AiTL PC Studio Design System — V0413

This is the authoritative presentation and interface-copy reference for PC Studio. Page/layout documents define information architecture; this document defines visual roles, color semantics, hierarchy, controls, states, and writing style.

## Design intent

PC Studio is a desktop engineering workbench for a local traffic-simulation and computer-vision prototype. It should look deliberate, quiet, and operational—not like a promotional AI dashboard. Information should be scannable before it is decorative.

## Current benchmark and decisions (V0413)

AiTL is a Windows-focused engineering console. Its desktop layout and interactions are informed by:

- [Fluent 2 color](https://fluent2.microsoft.design/color/) — neutral/brand/semantic role separation; functional emphasis rather than broad accent fills.
- [Fluent 2 layout](https://fluent2.microsoft.design/layout) — 4px spacing ramp and visual grouping.
- [Fluent 2 button](https://fluent2.microsoft.design/components/web/react/core/button/usage/) — one dominant primary action; neutral secondary and destructive actions.
- [Fluent 2 tablist](https://fluent2.microsoft.design/components/web/react/core/tablist/usage) — clear selected states and concise tab labels.
- [Material 3 surfaces](https://developer.android.com/develop/ui/compose/designsystems/material3) — layered tonal surface hierarchy rather than deep drop shadows.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) — 4.5:1 small text, 3:1 interactive graphics and meaningful visible keyboard focus.

### V0413 implementation parameters

| Element | Light | Dark | Decision |
| --- | --- | --- | --- |
| Main canvas | `#F3F6FA` | `#4D4E61` | User-selected slate backdrop |
| Main panel | `#FFFFFF` | `#55576A` | Opaque content surface |
| Primary text | `#172B45` | `#F9FAFF` | High-contrast hierarchy |
| Muted text | `#52677D` | `#D6D9E8` | Legible secondary data |
| Primary control | `#006F66` | `#57FFED` | Teal theme, readable on each background |
| Input/interactive border | `#7B8FA7` | `#AEB2C6` | 3:1+ contrast against light/dark fields |
| Controls | 40px minimum height | same | Consistent pointer/keyboard target |
| Page/panel spacing | 4px increments; 20–32px sections | same | Deliberate proximity hierarchy |
| Radius | 6/9/12px | same | Compact Windows-style geometry |
| Tab selection | underline/segmented active surface | same | Distinguishes selected state from action |
| Focus | 3px outline, 2px offset | same | Strong keyboard focus without changed tab order |

Interactive control selection (tabs, toggles, camera rows) uses teal emphasis plus a dot, underline or ring. Sidebar page navigation is intentionally quieter: solid neutral selected row with brighter text and no mint strip or dot. Mint filled buttons use a dark foreground, while light-mode dark-teal buttons use white. Hover must remain distinct from selected state. Status green/amber/red remains semantic; the camera and traffic visualization palette is independent of light/dark application chrome. Dataset, Analytics, Live AI and Settings forms now use shared roles rather than always-dark literal hex values.

## Color-role model

Most of the interface remains neutral. Color has a job.

### Primary

Primary identifies links, focus, and the dominant action in a workflow. Sidebar navigation deliberately uses neutral slate selection to avoid repeated accent decoration.

Light appearance:

| Role | Value |
| --- | --- |
| Primary | `#006F66` |
| Primary hover | `#00594F` |
| Primary active | `#00473F` |
| Primary surface | `#E1F5F1` |
| On primary | `#FFFFFF` |

Dark appearance:

| Role | Value |
| --- | --- |
| Primary | `#57FFED` |
| Primary hover | `#87FFF2` |
| Primary active | `#2BE6D2` |
| Primary surface | `#2F585A` |
| On primary | `#08312C` |

Use primary for:

- selected functional controls and keyboard focus;
- the main action in a panel, such as **Save**, **Start**, **Refresh**, or **Apply**;
- focus indication and links;
- informational emphasis where a brand/interaction role is appropriate.

Do not use primary merely to make a panel more interesting.

### Secondary

Secondary is deliberately sparse. It distinguishes selected/active secondary controls and continuous progress without competing with the main action.

Light: `#006F66` with `#FFFFFF` on-secondary.
Dark: `#57FFED` with `#08312C` on-secondary.

Use secondary for:

- checkbox/radio/range accent;
- progress bars;
- selected secondary states;
- current-observation or active-rule emphasis where “success” would be misleading.

Do not use secondary as a second general brand color across large surfaces.

### Neutral surfaces

The light appearance retains its established cool-neutral canvas (`#F3F6FA`) and white panels. The dark appearance uses user-selected slate roles instead of navy or glass.

| Role | Dark solid surface |
| --- | --- |
| Application canvas | `#4D4E61` |
| Sidebar | `#414354` |
| Sidebar brand box | `#333648` |
| Panel | `#55576A` |
| Raised panel/control | `#5A5C70` |
| Inset input | `#47495B` |
| Muted panel | `#505266` |
| Hover | `#616375` |
| Pressed | `#5B5D70` |
| Selected functional control | `#2F585A` |
| Selected sidebar page | `#5A5C70` |

A separate brand panel and muted uppercase section headings with subtle dividers distinguish sections from page buttons. Active navigation rows use neutral slate (`#5A5C70`), not mint. Hover uses `#505266`; keyboard focus remains mint. Junction cards have a full-width draggable title bar above a separate 3×3 layout: observation/status information is centered, while edge labels 1–4 occupy the north/east/south/west sides of that content area. Their responsive text wraps and card height adapts to content. Use solid surfaces for panel hierarchy; retain translucent fills only for image overlays and text selection.

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
