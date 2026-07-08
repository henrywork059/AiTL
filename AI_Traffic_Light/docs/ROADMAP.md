# Roadmap

## 0_0_0 — Initial skeleton

- Project folder structure.
- Placeholder PC frontend.
- Placeholder PC backend.
- Shared schemas.
- ESP-CAM firmware placeholder.
- Documentation.

## 0_0_1 — Documentation/version cleanup

- Correct old “Version 1 / 0.1.0” wording.
- Confirm versioning scheme as `0_0_x`.
- Clarify that the current project is a starter skeleton.
- Keep functional code unchanged except version labels/placeholders.

## 0_0_2 — PC mock GUI cleanup

Planned next small patch:

- Make mock API/frontend wording cleaner.
- Add stronger placeholder states.
- Add clearer frontend/backend start instructions.
- Prepare GUI components for future detection data.

## 0_1_0 — PC mock GUI connected to mock API

- Frontend fetches real mock API data.
- Live View page shows mock detections and zones from backend.
- Traffic-light simulator panel updates from backend.
- Confidence slider affects frontend filtering.

## 0_2_0 — Video/webcam input

- Open webcam/video file on PC.
- Show frames in GUI.
- Save frames to dataset folder.

## 0_3_0 — Pretrained object detection

- Add YOLO detection backend.
- Detect person/car/bus/truck/motorcycle/bicycle.
- Return detection JSON.
- Draw boxes in GUI.

## 0_4_0 — Zone counting and signal logic

- Add zone configuration.
- Count pedestrians and vehicles by zone.
- Add simple traffic-light state machine.

## 0_5_0 — ESP-CAM input

- Receive MJPEG stream from ESP-CAM.
- Add camera source manager.
- Compare ESP-CAM quality/FPS with webcam.

## 0_6_0 — Dataset capture and review

- Save frame + metadata + detection JSON.
- Review captured data.
- Mark sample as useful/bad.

## 0_7_0 — Training placeholder

- Add training configuration UI.
- Prepare dataset export format.
- Add model version registry.

## Future extensions

- Instance segmentation.
- Physical traffic light LED model.
- Multi-camera support.
- Object tracking.
- Slow-crossing safety extension.
