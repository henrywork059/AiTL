# Patch 0_5_15 — Interactive 3D Simulation Lab

**Branch:** `feature/interactive-3d-simulation`  
**Candidate:** `0_5_15` | **Previous:** `0_5_14` | **Accepted baseline:** `0_5_0`.

Adds an optional 3D Replay tab to the existing Simulation Lab. It displays perspective roads, markings, signal indicators and schematic queued vehicles/pedestrians using the *existing* experiment timeline. Orbit/pitch/zoom sliders, top view, Reset view, timeline scrubbing, Play/Pause, and Fixed/Adaptive switching are client-side only. No additional dependencies, backend routes, simulation engines, controllers, camera transport, dataset storage or physical signal outputs.

**Evidence limitation:** Timeline stores aggregate counts and phase labels, not trajectories or precise positions. 3D positions are illustrative and never represented as tracked vehicle/person locations. Signal display follows phase labels, not live hardware status. This is a replay of an isolated synthetic benchmark, not a live synchronized 3D twin.

**Acceptance:** Typecheck and build the frontend and run the repository's structure/tests with the branch checked out; start app and check a saved and new experiment, both modes, user controls and responsive layout. Local Windows runtime/real ESP checks and owner PASS remain pending.
