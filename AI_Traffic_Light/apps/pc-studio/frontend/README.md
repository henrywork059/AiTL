# PC Studio Frontend

V034 Camera Sources adds low-latency physical-camera presentation:

- Connect remains status/control only;
- Start Stream sends all camera settings plus target FPS;
- transport state shows persistent MJPEG;
- measured FPS and reconnect count are visible;
- preview uses backend `/api/camera/live.mjpeg` rather than status-poll-driven still images;
- simulation can temporarily pause the physical stream.

The frontend does not connect directly to the ESP MJPEG endpoint; the backend owns the single physical stream.
