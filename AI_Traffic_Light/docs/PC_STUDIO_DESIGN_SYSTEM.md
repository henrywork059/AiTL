# PC Studio Design System — V023 candidate

This document is the authoritative visual-style reference for the PC Studio frontend. It defines the shared visual language; page documentation such as `PC_STUDIO_GUI_LAYOUT.md` defines information architecture and page contents.

## Design direction

PC Studio is a desktop engineering/prototype workbench. It should look like a restrained operations console, not a consumer AI assistant or marketing site.

Use:

- solid neutral surfaces with clear layer separation;
- compact typography and spacing suitable for dense technical information;
- low elevation and mostly 1px borders;
- small 4–8px corner radii for ordinary controls and containers;
- one desaturated interaction accent;
- semantic success/warning/danger colors only when the meaning requires them;
- persistent labels and text explanations instead of relying on color alone.

Avoid:

- decorative full-page gradients;
- glassmorphism, backdrop blur, translucent floating cards, or glow effects;
- purple/neon coloring as a generic technology/AI signal;
- oversized 14–24px card radii;
- excessive pill-shaped controls (pills are reserved for compact status badges);
- decorative animation that does not communicate state;
- page-local raw colors when a shared semantic token already exists.

## Source layout

```text
src/styles.css                 stable shared CSS entrypoint
src/styles/tokens.css          authoritative design tokens
src/styles/base.css            document, typography, controls, focus treatment
src/styles/layout.css          application shell and responsive page grids
src/styles/components.css      reusable panels, navigation, status, tables, forms, overlays
src/pages/*.css                page-only layout/behavior styling when genuinely specific
```

`src/main.tsx` continues to import only `src/styles.css`. Shared styles must not be imported separately by pages.

Page-specific CSS may consume tokens but should not duplicate the palette. `signalRules.css` is currently the main example: it owns Traffic Logic-specific tabs/timing/rule layout while shared controls, surfaces, and colors come from the design system.

## Core visual tokens

| Role | Token | Current value / intent |
| --- | --- | --- |
| Canvas | `--color-canvas` | `#111315`, neutral application background |
| Shell | `--color-shell` | `#15181b`, sidebar/status shell |
| Surface | `--color-surface` | `#1b1f23`, standard panel |
| Raised surface | `--color-surface-raised` | `#20252a`, headers/selected neutral state |
| Field | `--color-field` | `#14171a`, inputs and code fields |
| Subtle border | `--color-border-subtle` | `#30363c` |
| Strong border | `--color-border-strong` | `#535d66` |
| Primary text | `--color-text-primary` | `#edf0f2` |
| Secondary text | `--color-text-secondary` | `#b8bec4` |
| Muted text | `--color-text-muted` | `#90979e` |
| Interaction accent | `--color-accent` | `#708e88`, muted/desaturated teal-gray |
| Focus | `--color-focus` | `#a8bdb6`, visible keyboard focus |
| Success | `--color-success` | muted green, successful/implemented states only |
| Warning | `--color-warning` | muted amber, warning/pending states only |
| Danger | `--color-danger` | muted red, errors/destructive states only |
| Information | `--color-info` | muted steel-blue, informational/code emphasis |

Detection/scene overlays use separate role tokens (`--color-person`, `--color-vehicle`, `--color-crossing`, `--color-queue`) so model/zone visualization remains distinguishable without leaking those colors into general application chrome.

## Typography

Use the native Windows/system UI stack:

```text
Segoe UI Variable Text → Segoe UI → system-ui
```

Do not add a webfont merely for visual novelty. Technical identifiers and endpoint/path text use the system monospace stack headed by Cascadia Code when available.

Hierarchy:

- page title: 26px, semibold;
- panel title: 16px;
- local/subsection heading: 14px;
- standard UI/body text: inherited browser/system size;
- metadata and status text: 11–12px.

Keep headings concise and functional. Avoid oversized hero typography inside the application shell.

## Spacing and geometry

The shared spacing scale is based on a 4px unit: 4, 8, 12, 16, 20, 24, and 32px. Prefer these tokens rather than arbitrary gaps.

Corner radii:

- small: 4px;
- normal controls: 6px;
- panels/media frames: 8px;
- 999px only for compact status pills or truly circular/pill geometry.

Panels use a subtle 1px border and minimal 1–2px shadow. Layer/background contrast, not a large shadow, provides hierarchy.

## Interaction rules

- Default buttons are neutral. Do not make every action a saturated primary button.
- Active navigation uses a neutral raised surface plus a narrow accent edge instead of a bright filled tile.
- Tabs use a restrained underline/edge treatment rather than a glowing filled chip.
- Inputs/selects/textareas share the same field surface and border.
- All interactive elements must retain an obvious `:focus-visible` outline.
- Disabled controls may use opacity, but text must remain readable.

## Status and semantic color

Color must communicate an existing state, not decorate the interface.

- green: success, implemented, healthy;
- amber: warning, pending, suppressed;
- red: error/danger;
- informational steel-blue: code/endpoint/information emphasis;
- accent: selection/focus/navigation, not health status.

Pair status color with text such as `active`, `warning`, `failed`, or a written explanation. Do not encode rule state by color alone.

## Research basis

This is an AiTL-specific design system, not a copy of another product. The architecture follows established guidance:

- IBM Carbon: role-based color tokens and neutral surface layering; AI-specific tokens are separate from ordinary product UI tokens.
  - https://carbondesignsystem.com/elements/color/tokens/
  - https://preview.carbondesignsystem.com/building-blocks/foundations/color/overview
- GitHub Primer: functional/component color tokens, responsive product foundations, and compact default geometry (6px default radius).
  - https://primer.style/product/getting-started/foundations/color-usage/
  - https://primer.style/product/primitives/size/
- Atlassian Design System: design tokens as the single source of truth for repeatable visual decisions.
  - https://atlassian.design/foundations/tokens/design-tokens/
- GOV.UK Design System: consistent spacing scales and established conventions rather than arbitrary one-off styling.
  - https://design-system.service.gov.uk/styles/spacing/

## Change rules for future patches

1. Reuse an existing token before introducing a new visual value.
2. Add new shared tokens only when the role is reusable across multiple surfaces.
3. Keep page CSS structural; avoid page-private palettes.
4. Do not bring back decorative gradients/glows/glass effects without an explicit owner request.
5. When changing the visual language, update this document and run frontend typecheck/build plus manual cross-page checks.
6. Keep the simulator/prototype safety wording visible where relevant; visual polish must never imply production public-road control capability.
