# Project Scope

## Physical camera input

V035 implements a local PC-controlled ESP32-CAM input path with:
- idle Connect;
- PC-owned runtime sensor configuration;
- persistent low-latency MJPEG;
- transport recovery after temporary network/session loss;
- common downstream use by preview, inference, dataset capture, zones and analytics.

This does not imply:
- ESP-side inference;
- validated production detector accuracy;
- simultaneous independent multi-camera buffers;
- physical/public-road traffic-signal authority.

Existing cooperation, pedestrian, class, emergency and explainability/evidence features retain their documented prototype/simulation provenance.
