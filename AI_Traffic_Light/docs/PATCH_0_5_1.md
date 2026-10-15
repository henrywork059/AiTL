# Patch 0_5_1 — Conceal simulation tools

Candidate `0_5_1`, previous stable/accepted baseline `0_5_0`.

The top-left **AI Traffic Light** panel toggles simulation-related UI by mouse or keyboard. By default it conceals Experiments navigation, simulated camera creation/options, simulator controls and previews on Camera Settings, Crosswalks, Region Editor and Junction Network. Currently active simulation and saved Crosswalk camera sources remain unchanged. The toggle does not provide backend access control, affect ESP camera hardware or modify traffic-signal safety.

Windows owner acceptance: run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests`, check simulator hidden/revealed states, camera assignments, ESP flows, startup and smoke. PASS pending.
