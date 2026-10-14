# Patch 0_3_26 — Numbered edges and saved simulation camera

Previous candidate: `0_3_25`; accepted baseline: `0_3_11` (unchanged).

In Junction Network, the four existing edge controls now show orientation-neutral numbers **1–4**. Creating a directed topology link records selected source and destination edge numbers in the established approach fields. Existing cardinally named storage keys remain unchanged for compatibility with previously saved crosswalk edge assignments.

In Camera Settings use **New camera → Simulation camera → Save** to register the single built-in simulated camera. No IP, ESP connection or firmware is required. Selecting it uses the shared simulated scene. It appears in Crosswalk camera selectors. Switching to a physical ESP restores receiver mode.

This is configuration and simulated preview only, not new traffic actuation or multi-camera inference. Run `python scripts/test_remote_camera_multi.py`, `python scripts/test_camera_settings_page_structure.py`, `python scripts/test_junction_network_frontend_structure.py` and `python scripts/test_intersection_network.py`; perform Windows runner / browser owner tests before PASS.
