# Patch 0_3_7 — Adaptive low-latency ESP streaming

V037 / `0_3_7` is a new candidate explicitly requested by the owner after V036. `passed_baseline` remains `0_2_4`.

## Why V037 exists

Physical V036 R6 testing proved the persistent TCP path could stay connected and complete frames, but typical JPEGs around 11–22 KB still produced 100–500+ ms sends and occasional timeout/reconnects. That load cannot sustain a 15 FPS freshness target because one 15 FPS frame budget is about 66.7 ms.

## Changes

- Keep the V036 `aitl-tcp-jpeg-v1` frame format and multi-ESP PC architecture.
- Firmware protocol identity becomes `aitl-camera-v037`; PC Studio accepts V037 and V036 binary-TCP nodes during migration.
- Add adaptive JPEG pressure control on each V037 ESP:
  - configured JPEG quality remains the best-quality floor;
  - slow/large successful frames increase compression in small bounded steps;
  - a failed send increases compression more aggressively;
  - sustained small/fast frames gradually recover toward the configured quality;
  - effective quality is capped at 40.
- Add ESP telemetry: `configured_jpeg_quality`, `effective_jpeg_quality`, `adaptive_quality_adjustments`, and `send_ewma_ms`.
- Serial status adds `q=<effective>/<configured>`, EWMA send time and adjustment count.
- New camera defaults become `QVGA / JPEG 24 / 15 FPS` in firmware, backend profile defaults and frontend defaults. Existing saved profiles are not rewritten.
- Preserve R6 non-blocking vectored `sendmsg`, TCP_NODELAY/keepalive, warm-up bounds, fresh-frame scheduling, multi-camera source selection and simulation behavior.

## Deliberate non-changes

- No UDP transport in V037; TCP remains the transport so this patch isolates the effect of adaptive payload sizing before a larger protocol change.
- No ESP-side AI/inference.
- No public-road or physical signal authority.
- No change to saved `config/remote_cameras.json` data.

## Acceptance target

At QVGA / saved JPEG quality 24 / target 15 FPS on the same LAN, V037 should converge to a smaller effective JPEG size and materially reduce average send time/reconnect growth compared with V036. Physical results, not automated tests alone, decide acceptance.
