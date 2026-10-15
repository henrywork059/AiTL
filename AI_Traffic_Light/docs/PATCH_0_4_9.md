# Patch 0_4_9 — Owner-approved slate and mint palette

Candidate: `0_4_9`; previous candidate: `0_4_8`; accepted stable baseline: `0_4_0`.

## Scope

- Shared dark CSS design tokens: user-chosen canvas `#4D4E61`, coordinated solid sidebar, brand, panel, nested/inset, selection, border, text and semantic colors. Retain `#57FFED` interactive accent and contrast-safe light teal `#006F66`.
- Sidebar brand/title gains a distinct panel, navigation group headings gain their own contrasting filled strips with mint markers; existing navigation and selection semantics remain unchanged.
- Junction Network 1–4 edge controls move inside the card via reserved 28px vertical and 32px horizontal insets. Card width adjusts to 284px (260px at narrow screens) to retain readable node content. Edge mapping/drag logic and saved junction positions stay unchanged.
- Add palette/contrast/sidebar/edge geometry regressions, update historical outside-label and old dark-base assertions. No new dependencies or traffic-control, camera or API changes.

## Validation

Source-level contrast checks use 4.5:1 text and 3:1 essential control-boundary targets on sampled combinations. Local Windows frontend build, runtime visual inspections at multiple sizes, backend smoke and hardware tests are not claimed as passed until tested. Use the established single-command update/test/run process.
