# AiTL 0_3_8 R5 Camera Transport Benchmark

This is a **diagnostic-only** same-candidate revision for the unaccepted `0_3_8` camera-diagnostics candidate. It does not promote the stable baseline and does not replace the normal V037 production firmware.

## Purpose

The R5 benchmark compares practical ESP32-CAM transport alternatives under the same camera settings so the next production fix is chosen from evidence rather than guesswork.

The benchmark separates:

- camera capture failure;
- repeated HTTP/camera pressure;
- current timeout behavior;
- `sendmsg()` vs ordinary `send()`;
- direct PSRAM socket access vs internal-DRAM staging/copy;
- custom raw TCP vs dedicated-port MJPEG;
- persistent TCP/backpressure vs freshness-first UDP;
- control responsiveness while streaming;
- internal heap / largest-block pressure;
- Wi-Fi environment dependence.


## R5 live progress display

R5 prints the current test location and frame progress by default. Example:

```text
--- MEMORY-SOURCE ISOLATION ---
[08] START  +  18.4s | ATL1 1460-B DRAM staging + send() | PSRAM copied in small DRAM chunks
     RUN     1/8  | ATL1 1460-B DRAM staging + send() | seq=41; 6127 B; recv=43.2 ms
     RUN     2/8  | ATL1 1460-B DRAM staging + send() | seq=42; 6059 B; recv=39.8 ms
     PASS   8/8 frames | 5.01 FPS | 1620 ms | staged_send
```

The run header also shows the ESP IP, PC local IP, environment label, camera resolution, JPEG quality, primary FPS and requested frame count. Use `--quiet` only if this progress display is not wanted.

## R5 detailed evidence retained in JSON

Each empirical result now retains, where applicable:

- device `/status` snapshot before and after the phase;
- transport-counter deltas;
- free heap, internal free RAM, largest internal block, minimum free heap and free PSRAM;
- RSSI, BSSID and Wi-Fi channel;
- up to 160 periodic `/status` samples during key persistent-stream phases;
- HTTP-control latency average/p95/max while streaming;
- per-frame payload sizes;
- ATL1 sequence numbers and source uptime;
- per-frame receive time and inter-arrival intervals;
- frame-interval average/p95/max/jitter;
- receiver exception text when a phase fails;
- ESP send duration, accepted bytes, errno and byte/time `progress_trace`;
- UDP frame sequences, chunk counts, malformed packets, duplicate chunks and incomplete frames at deadline;
- start/end timestamps for every test;
- total benchmark runtime and host/platform context.

The root `analysis_evidence` object adds direct A/B comparisons for:

- 1.2 s vs 5 s timeout;
- direct `sendmsg()` vs direct `send()`;
- direct PSRAM vs staged DRAM;
- direct PSRAM vs whole-frame DRAM copy;
- DRAM `sendmsg()` vs DRAM `send()`;
- real camera payload vs synthetic DRAM payload;
- ATL1/TCP vs MJPEG;
- persistent TCP vs UDP;
- snapshot polling vs MJPEG.

It also provides a hypothesis ranking so a later analysis can cite the evidence that supports each likely bottleneck rather than inferring from one final PASS/FAIL line.

## Empirical tests

| Test | What it isolates |
| --- | --- |
| Single HTTP `/capture` | camera + one HTTP JPEG response |
| Repeated `/capture` polling | safest independent-frame fallback and repeated capture/control pressure |
| Dedicated-port MJPEG | persistent HTTP JPEG stream using the camera and `WiFiClient.write()` |
| ATL1 direct PSRAM + `sendmsg()`, 1.2 s | current-like timeout/sender behavior |
| ATL1 direct PSRAM + `sendmsg()`, 5 s | whether the configured timeout itself is the material failure trigger |
| ATL1 direct PSRAM + plain `send()` | isolates vectored `sendmsg()` from direct PSRAM access |
| ATL1 1460-byte DRAM staging + `send()` | bypasses direct PSRAM-to-socket reads with low RAM demand |
| ATL1 full JPEG DRAM copy + `sendmsg()` | isolates memory source while retaining `sendmsg()` |
| ATL1 full JPEG DRAM copy + `send()` | strongest ATL1 production alternative if internal RAM is sufficient |
| Same-size synthetic DRAM + `sendmsg()` | TCP/lwIP control without real camera payload memory |
| Same-size synthetic DRAM + `send()` | plain-send TCP/lwIP control without real camera payload memory |
| UDP freshness-first JPEG | removes TCP backpressure/retransmission from the live transport comparison |
| Optional chunk sweep | 256 / 512 / 1024 / 1460 / 2920-byte staging comparison |
| 10/15 FPS load ladder | tests headroom only for live candidates that passed the primary 5 FPS comparison |

The script also polls `/status` during key persistent-stream phases. This shows whether image streaming blocks or starves HTTP control.

## Alternatives assessed but intentionally not benchmarked

These still appear in the final JSON report so the decision is explicit:

- **WebSocket binary JPEG** — still runs over TCP/lwIP. It adds handshake/framing code and cannot bypass a lower-layer TCP stall, so it is not a useful first isolation transport.
- **RTSP/RTP or H.264** — changes the stack/codec substantially and adds much more complexity than needed to diagnose the current OV2640 JPEG path.
- **Separate camera ESP + signal ESP** — a valid architecture/resource-isolation option, but not a same-device transport benchmark. Consider it if camera streaming and LED/control duties later contend on one node.

## Flash the diagnostic firmware

1. Extract the patch.
2. Open:

```text
AI_Traffic_Light\apps\device-camera\esp32-cam\arduino\AiTL_ESP32_CAM_TRANSPORT_DIAG\AiTL_ESP32_CAM_TRANSPORT_DIAG.ino
```

3. Copy `secrets.example.h` to `secrets.h` in the same sketch folder.
4. Enter the 2.4 GHz Wi-Fi SSID/password.
5. Flash with Arduino IDE using the same board settings that already work for the ESP32-CAM.
6. Open Serial Monitor at 115200 and note the ESP IP.

This firmware uses:

- port 80: control + snapshot;
- port 81: ATL1/TCP benchmark;
- port 84: dedicated MJPEG benchmark;
- UDP: outbound datagrams to a temporary PC port selected by the Python benchmark.

## Run the complete benchmark

From the repository root:

```powershell
python .\AI_Traffic_Light\scripts\test_camera_transport_benchmark.py --host 192.168.x.x --frames 8 --fps 5 --chunk-sweep --environment-label home-router
```

The default run also retests passing live candidates at 10 and 15 FPS. Add `--no-load-ladder` only when you want a shorter isolation run.

Output:

```text
camera_transport_benchmark.json
```

The report contains:

- per-test pass/fail;
- complete-frame ratio;
- measured FPS;
- bytes received;
- status-control successes/failures during streaming;
- UDP packet loss estimate;
- ESP send time / accepted bytes / errno;
- internal free heap / largest free block / minimum heap;
- free PSRAM;
- RSSI, BSSID and channel;
- send progress trace;
- ranked candidate transports;
- diagnosis code;
- recommended production path.

## Important diagnosis signatures

### Timeout is too aggressive

```text
sendmsg @ 1.2 s  FAIL
sendmsg @ 5 s    PASS
```

The timeout materially triggers the failure, but a multi-second JPEG send is still too slow for a healthy production stream.

### `sendmsg()` is the problem

```text
direct PSRAM sendmsg  FAIL
direct PSRAM send     PASS
```

Keep ATL1 and replace vectored `sendmsg()` with ordinary `send()`.

### Direct PSRAM-to-socket path is the problem

```text
direct PSRAM send     FAIL
staged DRAM send       PASS
or
full DRAM-copy send    PASS
```

Use the passing DRAM path for production.

### Custom TCP sender is the problem

```text
MJPEG                 PASS
ATL1 direct variants  FAIL
```

Dedicated-port MJPEG becomes the strongest fallback unless a DRAM ATL1 variant is also stable.

### Persistent TCP/backpressure is the problem

```text
snapshot polling  PASS
UDP               PASS
persistent TCP    FAIL
```

Focus on TCP/lwIP/backpressure/receiver draining before implementing another TCP wrapper such as WebSocket.

### General Wi-Fi/power/resource problem

```text
MJPEG         FAIL
DRAM ATL1     FAIL
UDP           FAIL
```

Do not choose a new protocol yet. Test AP/RF, router, 5 V supply and internal-memory pressure first.

## Environment A/B test

Run the exact same benchmark in at least two environments when failures are broad:

```powershell
python .\AI_Traffic_Light\scripts\test_camera_transport_benchmark.py --host <IP> --environment-label home-router
python .\AI_Traffic_Light\scripts\test_camera_transport_benchmark.py --host <IP> --environment-label hotspot
```

Use different output names, then compare:

```powershell
python .\AI_Traffic_Light\scripts\compare_camera_transport_reports.py .\home.json .\hotspot.json
```

If the diagnosis changes materially across networks, RF/router conditions are part of the failure. If the same sender-specific signature repeats, the firmware path becomes much more likely.

## PC Studio integration check

The R5 ATL1 phases deliberately use a minimal raw Python receiver: no UI, inference, image decode, browser relay or PC Studio frame service.

After this benchmark, restore the normal V037 firmware and run the existing V038 **Camera Diagnostics** managed-worker phase. Interpretation:

```text
R5 raw receiver PASS
V038 managed worker FAIL
```

means the remaining bottleneck is in PC Studio integration/backpressure rather than the ESP transport itself.

## Production decision order

The benchmark deliberately prefers the smallest stable change:

1. full-JPEG internal-DRAM copy + plain ATL1 `send()`;
2. 1460-byte staged DRAM + ATL1 `send()` when full-copy RAM is insufficient;
3. direct PSRAM + plain `send()` if only `sendmsg()` is bad;
4. dedicated-port MJPEG if the custom TCP sender remains unreliable;
5. independent `/capture` polling as the safest low-complexity fallback;
6. UDP only when TCP remains the isolated bottleneck and low-latency freshness is worth custom packet/reassembly logic.

Do not choose a transport solely because it has the highest raw FPS. Complete-frame stability and low stale-frame risk are more important for AiTL.
