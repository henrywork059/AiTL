# PC Studio Frontend

V037 Camera Sources supports saved multi-ESP32-CAM input while keeping one selected downstream source:
- save up to 12 ESP profiles with IP, source ID, target FPS and OV2640 settings;
- restore the last-selected camera and its settings after PC Studio restarts;
- connect/start/stop/disconnect each selected ESP independently;
- keep other ESP TCP JPEG streams running in the background for faster switching;
- switch the active preview/AI/capture source without mixing frames from different cameras;
- show target/measured FPS, reconnect/recovery/failure telemetry and source-sequence gaps;
- use the backend MJPEG relay for browser preview while each ESP→PC hop uses V037 binary TCP JPEG.

Camera switching is freshness guarded. An old cached frame is not promoted after the freshness window, and changing a saved IP invalidates the previous device/session cache. Simulation temporarily owns the shared frame pipeline and physical streams resume afterward.

V037 new-camera defaults are 320 × 240 / JPEG 24 / 15 FPS. The V037 ESP may temporarily raise the effective JPEG quality number to reduce transport pressure while preserving the saved value as the recovery floor.
