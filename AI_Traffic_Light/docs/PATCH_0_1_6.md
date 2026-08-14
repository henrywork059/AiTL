# Patch 0_1_6 — Live layout and controllable simulation scene

## Scope

V016 builds only on the passed V015 / `0_1_5` baseline. It does not replace capture, labeling, managed YOLO training, model management, or live inference.

## Implemented

- Fixed Live AI model-panel overflow by allowing long model IDs, model paths, and run folders to wrap within the available grid/card width.
- Reworked the PC synthetic camera scene so the road runs horizontally while the pedestrian crossing is a vertical travel corridor.
- Pedestrians now move top-to-bottom and vehicles move horizontally in opposite lane directions.
- Increased scene variation using deterministic per-scene randomization of population, positions, sizes, and motion speeds.
- Added **Light / Normal / Busy** simulation density presets.
- Added **Pause / Resume scene** so a synthetic frame can be frozen for inspection or dataset capture.
- Added `POST /api/camera/simulation/settings` through the existing thin-route/service architecture.
- Added `simulation_density` and `simulation_paused` to camera status.
- Added `X-Request-ID` to the binary camera-frame response to match the project API rule.
- Added focused service/API tests for crossing orientation, object motion direction, density validation, pause/resume, request IDs, and stable errors.

## API/error decisions

No new stable error codes were required. V016 reuses:

- `ATL-API-002` for invalid simulation-setting request values / validation.
- `ATL-CAMERA-004` when pause/resume is requested before simulation starts.

## Limitations

- The synthetic scene is deliberately simple OpenCV artwork, not a physics simulator or photorealistic traffic generator.
- Scene density changes visual test population only; it does not change real traffic logic.
- Live detections still do not feed real public-road signals or physical traffic infrastructure.
- Automatic labeling and model export remain outside this patch.

## Acceptance focus

The owner should verify the exact V016 checklist in `docs/TEST_READY_CHECKLIST.md`, especially Live AI text containment, top-to-bottom pedestrian motion, horizontal vehicle motion, density controls, pause/resume, capture regression, and V015 inference/model-management regression.
