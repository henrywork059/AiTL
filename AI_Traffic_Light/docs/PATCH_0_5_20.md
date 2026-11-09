# Patch 0_5_20 — Automated candidate CI

Branch: `feature/interactive-3d-simulation`. Candidate: `0_5_20`. Previous: `0_5_19`. Accepted baseline: `0_5_0`.

Adds a Windows Actions workflow for Python compilation, project structure, auto-discovered offline regression scripts (excluding live backend smoke and camera hardware benchmarks) and frontend npm typecheck/build. Does not change app behavior or enable hardware actuation. Inspect CI before making a PASS claim; local Windows startup/API, 3D interaction and ESP validation remain required.
