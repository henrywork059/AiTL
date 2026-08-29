# PC Studio Frontend

Camera Sources supports saved multi-ESP32-CAM input while keeping one selected downstream source:

- save up to 12 ESP profiles with IP, source ID, target FPS and OV2640 settings;
- restore the last-selected camera and its settings after PC Studio restarts;
- connect/start/stop/disconnect each selected ESP independently;
- keep other compatible ESP TCP JPEG streams running in the background for faster switching;
- switch the active preview/AI/capture source without mixing frames from different cameras;
- show target/measured FPS, reconnect/recovery/failure telemetry and source-sequence gaps;
- use the backend MJPEG relay for browser preview while the ESP→PC image hop uses binary TCP JPEG.

Camera switching is freshness guarded. An old cached frame is not promoted after the freshness window, and changing a saved IP invalidates the previous device/session cache. Simulation temporarily owns the shared frame pipeline and physical streams resume afterward.

The current quality-preserving ESP path keeps the configured JPEG quality and resolution fixed across transport pressure. New profile defaults are 320 × 240 / JPEG 24 / 15 FPS; existing saved profiles retain their values.

## Camera Test

Camera Diagnostics is a separate Operate page. With a saved camera selected, **Diagnose camera** runs one staged test and reports the most likely failing layer. The page covers ESP control reachability, firmware/camera readiness, Wi-Fi telemetry, direct ATL1/JPEG transport, stream behavior while status polling is active, and the normal PC Studio managed receiver path. Previous camera/simulation state is restored after the run where possible.
