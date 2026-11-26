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
V038 R2 Camera Test presents one-click functionality checks, a 0–100 stability score, detailed transport metrics, and explicit bottleneck attribution.

## Optional synthetic road renderer

Three.js 0.187.0 (MIT, exact pin) renders canonical 1280×720 synthetic road geometry, crossing, markings, pavements/kerbs, virtual signals and coarse agent proxies. SimulationCamera3D retains polling, camera controls and source matching; ThreeRoadView owns WebGL lifecycle and RoadRenderer is shared with the trial. Default CSS rendering is retained; select Three.js preview explicitly for compatible snapshots without visible region/detection overlays. Editor/overlay modes, incompatible or absent snapshots and WebGL failures fall back to legacy. Retry or select Legacy view. No API, coordinate, simulator/controller authority or physical output changes.

### Vehicle presentation

The opt-in Three.js preview uses distinct procedural car, SUV, van and bus meshes with body/cabin proportions, windows, wheels and lights. RoadRenderer retains mesh groups by backend vehicle slot ID and shape signature; removes absent groups and disposes owned materials. VehicleMotion interpolates authoritative observed centers and shortest-angle headings for at most 450 ms, without extrapolation or simulator-clock mutation. Large jumps, backwards straight movement, changed shape, source/density change, clock rollback or a gap over one simulation second reset the affected motion; pause/resume snaps to the authoritative pose. RequestAnimationFrame runs only during active interpolation. The legacy CSS renderer remains default and preserves editing/overlay fallback, camera coordinates and all backend APIs and signal authority. No dependency or physical output changes.
