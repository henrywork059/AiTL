# Project Scope

## Physical camera input

V034 implements a PC-controlled, on-demand physical ESP32-CAM path with persistent MJPEG transport for lower latency. The ESP still sends no images before the PC starts a session.

Implemented candidate evidence:
- private-LAN camera control;
- PC-owned sensor settings and target FPS;
- persistent newest-frame MJPEG ingestion;
- PC-side preview/inference/dataset/analytics reuse.

Not implied:
- validated detector accuracy;
- ESP-side inference;
- simultaneous independent multi-camera buffers;
- physical/public-road signal authority.

Existing cooperation, pedestrian, class, emergency and decision-evidence features retain their documented simulation/prototype provenance.

Public-road traffic control remains out of scope.
