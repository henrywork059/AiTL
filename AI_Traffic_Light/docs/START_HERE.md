# Start Here — V038

V038 / `0_3_8` is the current unaccepted candidate. V037 / `0_3_7` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Camera transport

V038 keeps the existing quality-preserving V037/R6 ESP firmware and `aitl-tcp-jpeg-v1` transport:

```text
PC Connect -> ESP /status only
PC Start -> /config -> /start -> persistent TCP :81
ESP -> ATL1 header + configured JPEG
selected ESP -> CameraFrameService -> preview / Live AI / capture / zones / analytics
```

Configured JPEG quality and resolution remain fixed across transport pressure. The camera firmware still reports `aitl-camera-v037`; V038 PC Studio accepts the same V037/V036-compatible binary TCP protocol, so this PC-side candidate does not require another ESP reflash.

## One-click Camera Diagnostics

Open **Operate → Camera Test** after saving/selecting an ESP in Camera Sources. Press **Diagnose camera** once. PC Studio automatically checks:

1. ESP `/status` reachability and latency;
2. camera/stream protocol compatibility and camera readiness;
3. RSSI/BSSID/channel telemetry;
4. direct ATL1/JPEG transport with the normal PC Studio receiver bypassed;
5. the same direct stream while `/status` polling runs;
6. the normal PC Studio managed stream worker;
7. restoration of the previous camera/simulation state.

The result reports a likely failing layer plus evidence and next action. Diagnostics use the saved image settings at 5 FPS temporarily and restore the saved target FPS/settings afterward.
V038 R2 expands **Camera Test** into a detailed one-click functionality/stability/bottleneck run. It measures control latency distribution, direct and concurrent-control streaming, saved-target throughput headroom, reconnect behavior, normal PC Studio worker performance, and restores the previous camera state.
