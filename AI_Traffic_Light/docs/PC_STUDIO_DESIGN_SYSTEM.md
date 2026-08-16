# PC Studio Design System — V023 candidate

This document is the authoritative visual-style reference for the PC Studio frontend. Page documents such as `PC_STUDIO_GUI_LAYOUT.md` define information architecture; this document defines visual hierarchy, color roles, typography, spacing, elevation, interaction states, and accessibility behavior.

## Design intent

PC Studio is a desktop engineering/prototype workbench. The interface should feel calm, precise, and platform-native rather than like a consumer AI assistant, promotional dashboard, or neon technology demo.

The design uses a restrained neutral foundation with one cool interaction family. Most of the screen is carried by background/surface/text values; color is reserved for interaction and genuine semantic state.

### Principles

1. **Hierarchy before decoration.** Separation comes from typography, spacing, base/elevated surfaces, and borders before color or shadow.
2. **Harmony through repetition.** The same tokens, radii, spacing steps, and interaction treatments repeat across pages.
3. **Consistency of meaning.** A color role must keep the same meaning everywhere. Interaction color is not reused as a health/status color.
4. **System adaptation.** The web UI follows the operating-system light/dark preference with `prefers-color-scheme`; there is no separate PC Studio appearance toggle.
5. **Legibility first.** Text/background pairs target at least WCAG AA 4.5:1 for normal text; muted text is still designed to remain readable.
6. **Color is supporting information.** Status text, labels, icons, borders, and written explanations remain present so color is never the only state cue.
7. **Motion is optional.** Cosmetic transitions are short and are effectively disabled when the user requests reduced motion.

## Research basis

The system is AiTL-specific; it does not copy the appearance of Apple, Figma, Material, or UX Pilot. Their guidance is used as design rationale:

- Apple Human Interface Guidelines — hierarchy, harmony, consistency, semantic/adaptive color, base/elevated dark surfaces, system appearance adaptation, and contrast guidance:
  - https://developer.apple.com/design/human-interface-guidelines
  - https://developer.apple.com/design/human-interface-guidelines/color
  - https://developer.apple.com/design/human-interface-guidelines/dark-mode
  - https://developer.apple.com/design/human-interface-guidelines/accessibility
- UX Pilot color-theory guide — keep palettes tight, assign explicit roles, use tones for understated dashboard polish, reserve accent color for key emphasis, and check text contrast:
  - https://uxpilot.ai/blogs/color-theory-in-web-design
- Figma color-theory resource — use color harmony deliberately; a dominant/support/accent relationship is preferable to unrelated competing hues; tune saturation/value and preserve accessibility:
  - https://www.figma.com/resource-library/what-is-color-theory/
- Material Design 2 color system and dark-theme properties — primary/secondary/background/surface/error roles, “on” colors, a `#121212` dark baseline, lighter surfaces at higher elevation, light/desaturated dark-theme accents, and sparse color use:
  - https://m2.material.io/design/color/the-color-system.html
  - https://m2.material.io/design/color/dark-theme.html#properties

## Palette model

The palette is intentionally narrow:

- **dominant:** neutral canvas/shell/surfaces;
- **supporting:** neutral text/border/elevated layers;
- **interaction accent:** one muted steel-blue family;
- **semantic exceptions:** green, amber, and red only for success/warning/danger and the actual simulated signal lamps;
- **visualization exceptions:** separate camera-overlay colors that do not leak into application chrome.

The often-cited 60/30/10 color heuristic is treated as a direction rather than a literal measurement: neutral surfaces occupy the overwhelming majority of the interface, supporting neutral layers provide hierarchy, and accent/semantic color remains sparse.

## Appearance adaptation

`src/styles/tokens.css` defines the light appearance first and overrides role tokens inside:

```css
@media (prefers-color-scheme: dark) { ... }
```

This follows the operating-system preference automatically. Do not add a separate app-specific light/dark switch unless the owner explicitly requests one.

Dark appearance is not a simple inversion. It follows the Material 2 dark-theme surface model more directly:

- the application canvas and navigation shell use the `#121212` baseline;
- raised surfaces become progressively lighter rather than relying on dark-theme shadows;
- interaction color uses a light/desaturated Blue Grey tone instead of a saturated blue/cyan/purple accent;
- light semantic tones appear only in small status/state regions;
- foreground hierarchy uses off-white/gray on-surface roles rather than pure white everywhere.

This creates depth through controlled luminance changes while leaving the overwhelming majority of the UI neutral.

## Source layout

```text
src/styles.css                 stable shared CSS entrypoint
src/styles/tokens.css          authoritative role tokens + light/dark variants
src/styles/base.css            document, typography, controls, focus/accessibility
src/styles/layout.css          shell, page hierarchy, responsive grids
src/styles/components.css      reusable panels/navigation/status/forms/tables/overlays
src/pages/*.css                genuinely page-specific layout only
```

`src/main.tsx` imports only `src/styles.css`. Pages may import page-specific CSS, but page CSS must consume shared tokens rather than define a second palette.

## Core role tokens

### Light appearance

| Role | Token | Value |
| --- | --- | --- |
| Canvas | `--color-canvas` | `#f5f5f5` |
| Shell | `--color-shell` | `#eeeeee` |
| Surface | `--color-surface` | `#ffffff` |
| Raised surface | `--color-surface-raised` | `#fafafa` |
| Field | `--color-field` | `#ffffff` |
| Primary text | `--color-text-primary` | `#212121` |
| Secondary text | `--color-text-secondary` | `#616161` |
| Muted text | `--color-text-muted` | `#757575` |
| Interaction accent | `--color-accent` | `#455a64` (Blue Grey 700) |
| Accent surface | `--color-accent-surface` | `#eceff1` |
| Focus | `--color-focus` | `#546e7a` |

### Dark appearance role mapping

| Role | Token | Value |
| --- | --- | --- |
| Canvas / shell | `--color-canvas`, `--color-shell` | `#121212` (0dp) |
| Surface / panel | `--color-surface` | `#1e1e1e` (1dp) |
| Raised control | `--color-surface-raised` | `#232323` (2dp) |
| Hover surface | `--color-control-hover` | `#272727` (4dp) |
| Pressed / overlay surface | `--color-control-pressed`, `--color-surface-overlay` | `#2e2e2e` (8dp) |
| Primary text | `--color-text-primary` | `#e0e0e0` |
| Secondary text | `--color-text-secondary` | `#bdbdbd` |
| Muted text | `--color-text-muted` | `#a0a0a0` |
| Interaction accent | `--color-accent` | `#b0bec5` (Blue Grey 200) |
| Accent hover | `--color-accent-hover` | `#cfd8dc` (Blue Grey 100) |
| Accent active | `--color-accent-active` | `#90a4ae` (Blue Grey 300) |
| Focus | `--color-focus` | `#cfd8dc` |


## Material dark surface ramp

Material 2's dark-theme model treats elevation as a luminance change: a neutral dark base receives progressively stronger light overlays as a surface rises. PC Studio encodes the commonly used 0/1/2/4/8dp levels as explicit tokens so components do not invent arbitrary dark grays.

| Conceptual elevation | Token | Surface |
| --- | --- | --- |
| 0dp / canvas | `--color-dark-surface-0` | `#121212` |
| 1dp / standard panel | `--color-dark-surface-1` | `#1e1e1e` |
| 2dp / raised control | `--color-dark-surface-2` | `#232323` |
| 4dp / hover emphasis | `--color-dark-surface-4` | `#272727` |
| 8dp / pressed/overlay emphasis | `--color-dark-surface-8` | `#2e2e2e` |

These tokens are an elevation vocabulary, not five interchangeable decorative grays. Normal desktop panels use the 1dp role; ordinary buttons use 2dp; hover/pressed feedback may move upward through the ramp. Dark panels deliberately have no default shadow because the surface-lightness difference already carries depth.

## Dark-theme color usage

- Large surfaces remain neutral. Do not fill major panels, page backgrounds, or navigation regions with the interaction color.
- Primary interaction uses the light/desaturated Blue Grey family so links, focus, selection, and active controls remain visible without producing high-chroma vibration against dark gray.
- Semantic green/amber/red/info tones are light enough to remain readable but are paired with approximately 10% tinted surfaces rather than large opaque blocks.
- Camera and traffic-signal visualization colors remain separate because those colors encode scene objects and simulated signal meaning, not application chrome.
- Text should not default to pure `#ffffff`; the high-emphasis role is `#e0e0e0`, with lower-emphasis roles stepping down through `#bdbdbd` and `#a0a0a0`.

## Semantic colors

Semantic color is not decorative:

- `--color-success`: healthy/implemented/successful;
- `--color-warning`: warning/pending/suppressed;
- `--color-danger`: failed/error/destructive;
- `--color-info`: code, endpoint, or informational emphasis;
- `--color-accent`: navigation, selection, focus, links, and active controls.

Traffic signal red/amber/green have their own scene tokens because those hues describe the simulated signal itself rather than general application state.

## Contrast targets

Normal text should meet at least 4.5:1 against its intended surface. On the dark 1dp panel (`#1e1e1e`), the current primary (`#e0e0e0`), secondary (`#bdbdbd`), and muted (`#a0a0a0`) roles all remain above that target. The dark base is also intentionally far below the light foreground values so the hierarchy remains readable across the defined elevation ramp.

Do not lower contrast to create a “soft” aesthetic. If visual hierarchy needs to recede, change weight, size, spacing, or surface role before making text difficult to read.

The CSS also responds to `prefers-contrast: more` by strengthening borders and promoting muted text toward the secondary-text role.

## Typography

Use the platform stack:

```text
Segoe UI Variable Text → Segoe UI → system-ui → -apple-system
```

This avoids an unnecessary branded webfont and makes the Windows desktop development environment feel native. Technical identifiers use Cascadia Code when available, then the system monospace fallback chain.

Hierarchy:

- page title: 26px, semibold;
- panel title: 16px;
- subsection heading: 14px;
- body/control text: system default;
- metadata/status: 11–12px.

No hero typography is used inside the application shell.

## Spacing, shape, and elevation

Use the 4px rhythm: 4, 8, 12, 16, 20, 24, and 32px.

Corner radii remain compact:

- 4px for small geometry/progress tracks;
- 6px for controls and small containers;
- 8px for panels/media frames;
- pill geometry only for compact statuses or inherently circular/pill controls.

Use borders and surface-value changes for depth. Panel shadow is deliberately minimal. Do not introduce decorative glow, backdrop blur, glass effects, or large floating-card shadows.

## Navigation and controls

- Sidebar navigation is neutral by default.
- Active navigation uses a subtle accent-tinted surface plus a 2px accent edge; it does not become a saturated tile.
- Traffic Logic tabs use an underline/edge rather than filled rounded chips.
- Buttons are neutral by default; do not make every button a saturated primary CTA.
- Links, selection controls, checkboxes/radios/ranges, focus rings, and selected navigation share the interaction accent family.
- Hover and pressed states use nearby tones of the same role rather than introducing new hues.

## Status and visualization

Status badges may use semantic color because their purpose is state communication. They must also include readable words such as `active`, `warning`, `failed`, or equivalent contextual text.

Camera overlays are an exception to the application palette because they must stay legible over arbitrary imagery. Overlay labels remain high-contrast white-on-dark even when the rest of the application is in light appearance.

## Accessibility behavior

- `:focus-visible` uses a clear 2px focus outline.
- `prefers-reduced-motion: reduce` effectively removes nonessential transitions/animations.
- `prefers-contrast: more` increases border/text differentiation.
- `forced-colors: active` is not blocked by custom forced-color overrides.
- Do not encode state by color alone.
- Test both system light and dark appearances before accepting a visual patch.

## Avoid

- decorative full-page gradients;
- purple/cyan neon “AI” styling;
- glow effects and animated technology decoration;
- glassmorphism/backdrop blur as a default surface treatment;
- multiple unrelated accent hues competing for attention;
- page-local hard-coded UI colors when a role token exists;
- arbitrary dark grays that bypass the shared Material-derived elevation ramp;
- oversized card radii and excessive pill controls;
- low-contrast gray text used only to appear sophisticated;
- app-specific appearance controls that fight the operating-system preference.

## Change rules for future patches

1. Reuse an existing semantic/role token before creating a new value.
2. New shared tokens must describe a reusable role, not a one-page color preference.
3. Page CSS should be structural and consume the shared palette.
4. Keep neutral surfaces dominant and interaction color sparse; in dark appearance use the defined elevation ramp rather than shadows or arbitrary surface colors.
5. Preserve semantic meanings of success/warning/danger/accent.
6. Validate light mode, dark mode, keyboard focus, and reduced-motion behavior for visual changes.
7. Run frontend typecheck/build and `scripts/check_structure.py` after design-system changes.
8. Visual polish must not imply production/public-road traffic-control capability; AiTL remains a simulation/recommendation prototype.
