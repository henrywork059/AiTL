# Patch 0_3_3 — PC-controlled on-demand ESP camera session

## Release state

- Candidate: V033 / `0_3_3`
- Previous candidate: V032 / `0_3_2`
- Passed baseline: V024 / `0_2_4`

## Goal

Keep the ESP camera idle until PC Studio explicitly starts a session, and make PC Studio the authority for runtime OV2640 camera settings.

## PC workflow

1. **Connect** — probe `/status`; no image request.
2. Edit camera settings.
3. **Start Stream**:
   - send full settings to ESP `POST /config`;
   - call `POST /start`;
   - start bounded PC `/capture` polling.
4. **Stop Stream**:
   - stop PC polling;
   - call `POST /stop`;
   - ESP returns to idle.
5. **Disconnect** — stop best-effort then clear the PC device connection.

## New PC API

- `POST /api/camera/remote/start`
- `POST /api/camera/remote/stop`

`POST /api/camera/remote/connect` now establishes status/control only and deliberately does not fetch an image.

## PC-controlled settings

- frame size: QQVGA / HQVGA / QVGA / CIF / VGA / SVGA / XGA / SXGA / UXGA;
- JPEG quality 4–63;
- brightness / contrast / saturation;
- special effect;
- auto white balance / AWB gain / WB mode;
- auto exposure / AEC2 / AE level / AEC value;
- auto gain / AGC gain / gain ceiling;
- black/white pixel correction;
- raw gamma / lens correction;
- horizontal mirror / vertical flip;
- downsize/crop;
- color bar;
- PC capture interval 100–5000 ms.

## Matching firmware

V033 Arduino firmware adds:

- `GET /status`
- `POST /config?...`
- `POST /start`
- `POST /stop`
- gated `GET /capture`
- gated `GET :81/stream`

Image endpoints return a conflict while the session is idle.

## Deliberate non-changes

- legacy raw device POST receiver remains;
- simulation remains;
- inference/training/analytics/signal/network logic remains PC-side;
- no persistent PC remote-camera configuration yet;
- no independent simultaneous multi-camera frame store yet;
- no public-road traffic control.
