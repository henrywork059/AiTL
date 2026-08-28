# PC Studio Backend

V033 separates remote ESP control connection from frame transfer.

`RemoteCameraService` owns:

- private-LAN device/status probing;
- complete camera-setting translation to ESP `/config`;
- `/start` / `/stop` session lifecycle;
- bounded `/capture` polling worker;
- simulation pause/resume and shutdown cleanup.

It does not own inference or signal policy.

Existing CameraFrameService, dataset, inference, zones, analytics, signal rules and experiment services remain the downstream owners of their respective behavior.
