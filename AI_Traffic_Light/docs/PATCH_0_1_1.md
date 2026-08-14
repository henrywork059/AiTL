# Patch 0_1_1 — Camera frame receiver and simulation

## Purpose

Prepare PC Studio before ESP32/Raspberry Pi firmware development. The PC can now accept, validate, retain, and display the newest camera image.

## User workflow

1. Start the PC Studio backend and frontend.
2. Open **Camera Sources**.
3. Use **Start simulation** to test automatic frame refresh without hardware.
4. Stop simulation to return to receiver mode.
5. A future camera node sends raw JPEG/PNG bytes to `POST /api/camera/frame?source_id=<camera_id>`.
6. The new frame appears automatically within about one second.

## Boundaries

- The latest frame is held in memory and is cleared when the backend restarts.
- This patch does not implement ESP32/Raspberry Pi firmware.
- This patch does not run AI detection or control physical traffic lights.
