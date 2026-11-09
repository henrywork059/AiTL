# Patch 0_5_17 — Interactive 3D simulation regression test ordering

**Branch:** `feature/interactive-3d-simulation` | **Candidate:** `0_5_17` | **Previous:** `0_5_16` | **Accepted baseline:** `0_5_0`.

## Confirmed issue

The focused 3D simulation test saved an agent snapshot, then requested another frame before comparing the snapshot with the service's current agents. Frame retrieval refreshes the running simulation, so moving coordinates could change between those operations and fail the equality assertion despite correct snapshot behavior.

## Minimal repair

Compare the scene snapshot against the service agents immediately after reading the scene, then request the frame. This changes only test ordering; no runtime code, API, safety behavior, data, or rendering changes.

## Validation

Run `python scripts/test_v0515_3d_simulation.py`, `python scripts/test_camera_frame_service.py`, `python scripts/test_camera_simulation_api.py`, `python scripts/test_crosswalks_frontend_structure.py`, and `python scripts/check_structure.py`; run frontend `npm ci`, `npm run typecheck`, and `npm run build` where supported. Windows startup, live visual/region editing, physical ESP preview, and owner PASS remain required before acceptance. This patch remains a candidate; do not merge it into `main` or update `passed_baseline` without explicit owner PASS.

**Windows command (PowerShell at repository root):** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`
