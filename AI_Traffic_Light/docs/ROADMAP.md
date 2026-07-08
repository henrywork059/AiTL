# Roadmap

## Version 1 / 0.1.0 — Skeleton

- Project folder structure.
- Placeholder PC frontend.
- Placeholder PC backend.
- Shared schemas.
- ESP-CAM firmware placeholder.
- Documentation.

## Version 2 / 0.2.0 — PC mock GUI

- Frontend fetches real mock API data.
- Live View page shows mock detections and zones.
- Traffic-light simulator panel updates from backend.
- Confidence slider affects frontend filtering.

## Version 3 / 0.3.0 — Video/webcam input

- Open webcam/video file on PC.
- Show frames in GUI.
- Save frames to dataset folder.

## Version 4 / 0.4.0 — Pretrained detection

- Add YOLO detection backend.
- Detect person/car/bus/truck/motorcycle/bicycle.
- Return detection JSON.
- Draw boxes in GUI.

## Version 5 / 0.5.0 — Zone counting

- Add zone configuration.
- Count pedestrians and vehicles by zone.
- Add simple state machine.

## Version 6 / 0.6.0 — ESP-CAM input

- Receive MJPEG stream from ESP-CAM.
- Add camera source manager.
- Compare ESP-CAM quality/FPS with webcam.

## Version 7 / 0.7.0 — Dataset capture and review

- Save frame + metadata + detection JSON.
- Review captured data.
- Mark sample as useful/bad.

## Version 8 / 0.8.0 — Training placeholder

- Add training configuration UI.
- Prepare dataset export format.
- Add model version registry.

## Future

- Instance segmentation.
- Physical traffic light LED model.
- Multi-camera support.
- Object tracking.
- Slow-crossing safety extension.
