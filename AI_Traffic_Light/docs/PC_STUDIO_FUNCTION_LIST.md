# PC Studio Function List — current highlights

## Camera

- physical ESP32-CAM control connection by private-LAN IP;
- V033 explicit idle / Start Stream / Stop Stream lifecycle;
- complete PC-owned runtime OV2640 settings sent before each stream start;
- bounded repeated `/capture` polling only after ESP session activation;
- simulation pause/resume of physical frame requests;
- legacy raw JPEG/PNG upload compatibility;
- common frame pipeline for Live AI, Dataset Capture, zones and analytics.

## Existing PC Studio capabilities

- local trained-model inference;
- dataset capture/review/manual labeling/managed YOLO training;
- model registry;
- camera-aligned zones/counting lines;
- occupancy/tracking/flow analytics;
- configurable protected simulated signal timing and ranked scenarios;
- deterministic single-junction simulation lab;
- isolated two-intersection cooperation/pedestrian/class/emergency experiment modes;
- persistent normalized decision evidence.

## Limitation

Live non-simulation camera storage is still one latest-frame slot, not independent simultaneous buffers for multiple ESP cameras.

Physical/public-road signal control remains outside scope.
