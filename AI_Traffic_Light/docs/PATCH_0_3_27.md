# Patch 0_3_27 — Camera Settings preview regression assertion repair

Version: `0_3_27`  
Previous candidate: `0_3_26`  
Owner-confirmed passed baseline: `0_3_11` (unchanged)

## Failure and repair

V0326 Windows startup stopped at `test_camera_settings_page_structure.py:30` because the assertion searched for the obsolete text `selectedSaved && selectedStreaming && !status?.simulation_enabled`. The current Camera Settings preview deliberately separates the simulated camera and ESP paths, using `selectedSimulation && status?.simulation_enabled` and `selectedSaved && !selectedSimulation && selectedStreaming && !status?.simulation_enabled` respectively.

The focused test now verifies both explicit paths rather than the superseded ESP-only string. Runtime source and transport remain untouched. No configuration, hardware, signal, region or network behavior changes.

## Validation

Source-level static checks of both preview conditions and the updated assertion succeeded. The complete Python regression, frontend compilation, Windows update/test/run workflow and UI/hardware behavior require the owner's local environment. Candidate remains pending owner PASS.
