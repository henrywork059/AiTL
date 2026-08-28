# PC Studio Backend

V034 keeps the V033 remote-camera control lifecycle but changes the image transport to one persistent MJPEG connection.

`RemoteCameraService` owns:
- private-LAN status/control;
- full camera-setting + target-FPS configuration;
- ESP start/stop lifecycle;
- persistent `:81/stream` ingestion;
- incremental JPEG extraction;
- reconnect/FPS/byte telemetry;
- simulation pause/resume and bounded shutdown.

`CameraFrameService` remains the shared downstream latest-frame/simulation owner. Inference, dataset, zones, analytics and signal logic remain separate services.

`GET /api/camera/live.mjpeg` relays current PC-side frames to Camera Sources without opening a second browser→ESP stream.
