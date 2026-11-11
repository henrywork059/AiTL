# Patch 0_5_32 — Explicit simulation tools control

Candidate `0_5_32`, previous `0_5_31`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

## Hallmark audit and focused correction

The shared sidebar brand was an entire clickable `div` that silently toggled simulation tools. It required custom keyboard handling and duplicated the candidate version already present in the persistent status bar. The existing legacy-page headings also repeated “Legacy” in a separate eyebrow.

- Keep the brand panel informational and replace its hidden click action with a labeled native `Simulation tools` button using the existing toggle handler and `aria-pressed` state.
- Remove the duplicate sidebar version, workbench tagline and redundant legacy eyebrow. Retain page descriptions where they explain the task, plus the persistent version/status bar.
- Reuse existing light/dark tokens, focus-visible behavior, button styles and navigation rules; no new dependencies, routing, backend logic or simulated/physical signal changes.
- Keep `App.tsx` state restoration, including navigating away from Simulation Experiments when the tools are hidden, untouched.

## Verification

- Offline regression: `python scripts/test_v0532_hallmark_shell.py` checks semantic button, state/wiring, no hidden brand activation, responsive shell styling, and preserved version and legacy/navigation information.
- Existing related checks: `python scripts/test_v0401_navigation.py`, `python scripts/test_v0409_palette_layout.py`, `python scripts/test_v0413_quiet_navigation.py`, and `python scripts/test_v0422_responsive_layout.py`.
- Candidate CI should run the full offline suite, structure checker and frontend TypeScript/build. Windows owner validation is still required; no automated browser screenshots or physical tests are claimed.

## Owner validation

From the repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Check light/dark desktop and narrow layouts; the branding no longer toggles tools; clicking or keyboard-activating the labeled button opens/closes the Simulation Experiments entry with visible selected state; other navigation and runtime behavior are unchanged. Candidate requires explicit owner PASS.
