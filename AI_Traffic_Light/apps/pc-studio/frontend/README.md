# PC Studio Frontend

V035 Camera Sources keeps the V034 workflow and adds clearer transport diagnostics:
- MJPEG connected vs reconnecting;
- target/measured FPS;
- reconnect count;
- automatic session-recovery count;
- current failure streak/backoff;
- stale-frame drops.

The preview remains the backend MJPEG relay; the browser does not open a second ESP connection.
