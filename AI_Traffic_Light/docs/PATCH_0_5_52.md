# V0552 — Camera transport diagnostics

Candidate `0_5_52`, previous `0_5_51`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`. Roadmap Update 08 / H05.

Use a monotonic receive clock for frame intervals and smoothed FPS; reset interval and source-sequence baselines on TCP reconnect. Count repeated wire frames without publishing them twice, retain cumulative sequence gaps and count detectable in-session source resets. Expose cached original-frame age, stale/connection state, counters and last error in the existing camera status response and compact detailed panel. All diagnostics are passive: no extra JPEG decoding or public-road output.

The sequence gaps counter counts inferred missing sequence numbers *within* a TCP connection, not IP packet loss or a guaranteed count across disconnects. Reconnect attempts are existing failure/retry attempts, not confirmed successful reconnects. Frame age is based on the original PC receive timestamp (not ESP acquisition latency). Stale means disconnected or older than 5000 ms while streaming; stale FPS is displayed as unavailable. Values reset on explicit stream start; no hardware endurance measurement or latency certification is implied.

Focused zero-argument regression added: `scripts/test_v0552_camera_transport_diagnostics.py`. A full repository checkout, Python regression suite, structure guard, frontend build, CI results and real ESP/Windows test were **not run/verified in this environment**. Owner PASS pending.

See [Patch 0_5_52](PATCH_0_5_52.md).

## Owner validation

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Confirm two ESP sessions remain independent, disconnect/stale state is explicit, repeated sequence frames do not advance the selected frame, reconnect/restart counters and FPS recover, and no changes to TCP JPEG compatibility, settings, safe simulation transitions or hardware outputs.

Next: Update 09 / H05 — reusable endurance benchmark with separately labeled synthetic fixture and real-hardware test evidence.
