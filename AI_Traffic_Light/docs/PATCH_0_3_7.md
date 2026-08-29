# Patch 0_3_7 — Quality-preserving low-latency ESP streaming

V037 / `0_3_7` remains an unaccepted candidate. `passed_baseline` remains `0_2_4` until explicit owner acceptance.

## R6 diagnosis

R2/R4 assumed that a complete JPEG should fit roughly one classic ESP32 lwIP send-buffer window. Physical isolation testing disproved that assumption.

- Wi-Fi-only testing could remain stable for minutes with no disconnects.
- Camera isolation with `fb_count=1`, `CAMERA_GRAB_WHEN_EMPTY` and 20 MHz XCLK remained stable during 299 QVGA JPEG captures with zero capture failures and zero Wi-Fi disconnects.
- A separate TCP-only sender, with no camera initialized, successfully sent 8 KiB, 16 KiB and 32 KiB ATL1-framed payloads. Across the connected phases it completed 1040 sends with zero send failures, zero Wi-Fi disconnects and one persistent client connection.
- 16 KiB and 32 KiB payloads took longer to send, proving a throughput limit rather than a frame-size validity limit.
- The same SSID was observed on different BSSIDs with very different RSSI, so weak mesh/AP association can still create transient transport pressure.

The earlier R4 failure chain was therefore self-amplifying: a transient slow/failed send could be interpreted as a JPEG-size problem, drive `effective_jpeg_quality` to 50, lower effective resolution repeatedly, and permanently damage image quality even though larger JPEGs are valid over TCP.

## R6 changes

- Keep camera protocol `aitl-camera-v037` and wire protocol `aitl-tcp-jpeg-v1`; the fixed `ATL1 | length | sequence | uptime | JPEG` record is unchanged.
- Keep 20 MHz camera XCLK.
- Change the PSRAM camera pipeline to one framebuffer with `CAMERA_GRAB_WHEN_EMPTY`; remove the R4 two-buffer `CAMERA_GRAB_LATEST` configuration that kept the capture/DMA path continuously active.
- Allocate the single PSRAM framebuffer at UXGA capability so saved profiles can still select any supported runtime resolution.
- When a new TCP client connects, discard the frame that may have been waiting while idle so the first transmitted frame is fresh.
- Remove the 5000-byte target, 3800-byte learned minimum, partial-send window learning, local oversize rejection, automatic q=50 pressure escalation, and automatic effective-resolution downshift/recovery.
- Preserve the configured JPEG quality and frame size across network failures. A failed partial length-prefixed frame closes that client socket and waits for PC reconnect instead of degrading future images.
- Retain the proven non-blocking vectored `sendmsg(..., MSG_DONTWAIT)` path with `select()` progress waits, `TCP_NODELAY`, keepalive, and per-connection warmup.
- Relax normal send guardrails to 700 ms no-progress / 1500 ms total and warmup guardrails to 1200 ms / 2000 ms. These are failure guardrails, not image-quality adaptation triggers.
- Keep freshness-first scheduling: when transmission takes longer than the requested frame interval, the ESP schedules from the current time instead of queuing catch-up frames. Achieved FPS therefore falls naturally to sustainable throughput.
- Add RSSI, BSSID, channel, Wi-Fi disconnect count, reconnect count and last disconnect reason to `/status` and serial diagnostics.
- Keep legacy adaptive telemetry keys at zero for UI/API compatibility during the same V037 candidate.
- PC Studio's existing automatic persistent-TCP reconnect/session-recovery worker remains unchanged; manual **Disconnect** still intentionally stops reconnection and clears the selected live connection.

## R7 control-connection reliability repair

Physical R6 streaming could remain healthy, but repeated manual **Connect** attempts sometimes returned HTTP 502 while the ESP serial log still showed `wifiDisc=0` / `wifiRec=0` and the station remained on the same BSSID. The failed attempts correlated with transient RSSI around roughly -72 to -74 dBm. PC Studio also polls `/api/camera/remote/status` in parallel with button actions, while the ESP Arduino `WebServer` is single-threaded.

R7 therefore hardens only the PC control plane:

- Serialize all HTTP control operations per `RemoteCameraService` so background status refresh, Connect, Start/Stop and recovery cannot overlap requests to the same ESP.
- Retry transport-level control failures up to three times on fresh HTTP connections with short bounded backoff. This specifically covers timeouts/socket failures where the ESP may still be associated and recover on the next packet exchange.
- Keep `/status`, `/config`, `/start` and `/stop` semantics unchanged; these operations are idempotent, so retrying a lost control transaction is safe.
- Do not retry real HTTP responses, validation errors or protocol incompatibility; deterministic failures still surface immediately.
- Keep the Start sequence serialized across best-effort `/stop` -> `/config` -> `/start` so UI polling cannot interleave the sequence.
- No ESP firmware reflash is required for R7. The R6 quality-preserving camera/TCP data plane is unchanged.

## Deliberate non-changes

- No UDP transport.
- No protocol/version promotion.
- No rewrite of saved `config/remote_cameras.json` profiles.
- No ESP-side AI/inference.
- No public-road or physical signal authority.
- V036 binary-TCP camera nodes remain accepted by PC Studio during migration.

## Acceptance target

Test R6 first at QVGA / JPEG quality 20–24 / 5–15 FPS. Image quality must stay at the saved setting; `effective_jpeg_quality` must equal `configured_jpeg_quality`, effective frame size must equal the saved frame size, and old adaptive counters/targets must remain zero. Under a healthy BSSID/RSSI the stream should remain connected. Under a transient weak link the current socket may reconnect, but the firmware must not lower JPEG quality or resolution as a side effect.
