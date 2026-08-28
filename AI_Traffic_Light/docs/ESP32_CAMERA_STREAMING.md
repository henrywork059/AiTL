# ESP32-CAM V033 integration

## Required matching firmware

Use `AiTL_ESP32CAM_V033_ArduinoIDE.zip`.

The ESP stores only:

- Wi-Fi SSID/password;
- device ID;
- hostname.

Camera quality/resolution/exposure/gain/image settings are not configured in `secrets.h`. PC Studio sends them each time Start Stream is pressed.

## Idle behavior

After boot:

```text
Wi-Fi connected
control server ready
session=idle
```

`GET /status` works, but `/capture` and `:81/stream` do not return images until `POST /start`.

## Start sequence

PC Studio performs:

```text
POST /config?<complete camera settings>
POST /start
GET /capture
GET /capture
GET /capture
...
```

Stop Stream performs `POST /stop`.

This means image transfer is demand-driven from the PC.

## Browser diagnostic

Before PC Start Stream, `/status` should show:

```json
"session_active": false
```

After PC Start Stream it becomes `true`, and capture counters should rise as PC Studio requests images.

## Network

PC and ESP must be mutually reachable on the same private LAN. V033 PC Studio accepts literal RFC1918 IPv4 targets only.

## Limitation

One backend latest-frame slot remains shared for the live non-simulation camera path. Independent simultaneous multi-camera retention is a later patch.
