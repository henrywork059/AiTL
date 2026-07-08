# Start Here

## What to build first

Do **not** start with ESP-CAM, segmentation, or custom model training.

Start with the PC Studio App in mock mode:

```text
1. Open the placeholder GUI.
2. Check the live-view layout.
3. Check the traffic light simulator panel.
4. Check the fake detection counts.
5. Replace fake data with webcam/video frames.
6. Add object detection.
7. Add zone counting.
```

## First technical milestone

The first real working milestone is:

```text
A PC app that opens a video/webcam, detects pedestrians and vehicles, counts them inside predefined zones, and shows a simulated traffic-light decision.
```

## Suggested development order

1. Run frontend placeholder.
2. Run backend mock API.
3. Connect frontend to backend.
4. Add video/webcam frame reading.
5. Add YOLO detection.
6. Add zone counting.
7. Add traffic-light decision logic.
8. Add dataset capture.
9. Add ESP-CAM MJPEG input.
10. Add training/export tools.

## Avoid in the initial skeleton stage

- Real traffic-light control.
- License plate recognition.
- Disabled-person classification.
- Emergency vehicle priority.
- Multi-camera synchronization.
- Segmentation.
- Database.
- Cloud deployment.

These can be later extensions after the core demo works.
