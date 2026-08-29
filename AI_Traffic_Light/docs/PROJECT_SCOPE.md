# Project Scope

## Physical camera input

AiTL implements a local PC-controlled ESP32-CAM input path with:

- idle Connect/status probing with zero image transfer;
- PC-owned OV2640 runtime configuration;
- persistent low-latency length-prefixed TCP JPEG image transport;
- quality-preserving V037/R6 behavior that keeps configured JPEG quality and resolution fixed across transport pressure;
- transport/session recovery after temporary network or ESP restart;
- a persistent list of saved ESP private-LAN IP addresses and per-camera settings;
- several independent ESP stream workers/newest-frame caches that may run concurrently;
- explicit user selection of exactly one ESP to feed the shared preview, inference, dataset capture, zones/tracking and analytics pipeline;
- a V038 one-click diagnostic workflow that isolates control reachability, firmware/camera readiness, Wi-Fi margin, direct camera TCP transport, control/stream contention, and the normal PC Studio managed receiver path.

Source switching is freshness-guarded: the previous selected physical frame is cleared during a switch, a cached frame is promoted only when it is recent, and replaced device sessions are generation-guarded so late old-IP frames are rejected. This prevents an old or wrong-source image from being presented as a new active AI input.

Camera diagnostics are local prototype evidence. A run may temporarily quiesce the selected stream/simulation, measure the selected camera using its saved image settings at a conservative target FPS, and restore the prior state. A diagnostic label identifies the most likely failing layer; it is not a certification of network, detector, or camera reliability.

This does not imply:

- ESP-side inference;
- validated production detector accuracy;
- simultaneous independent inference/traffic-controller pipelines for all connected cameras;
- automatic cross-camera object identity/transfer matching;
- physical/public-road traffic-signal authority.

Existing cooperation, pedestrian, class, emergency and explainability/evidence features retain their documented prototype/simulation provenance. Multiple physical camera inputs are a data-source foundation for later multi-intersection work; they do not by themselves activate live cooperative control.
