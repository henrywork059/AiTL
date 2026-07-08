# Device Camera App

This folder contains camera-node code and instructions.

Version 1 treats the camera device as a **frame sender only**.

The PC does:

- AI inference
- detection/segmentation
- training
- GUI
- data saving

The camera device does:

- Wi-Fi connection
- camera capture
- MJPEG/JPEG stream

## Recommended first hardware options

1. Webcam connected directly to PC.
2. Phone/IP camera stream.
3. ESP32-CAM MJPEG stream.

Use webcam/video first. Add ESP32-CAM after the PC app works.
