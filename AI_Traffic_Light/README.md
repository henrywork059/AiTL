# AI Traffic Light (AiTL)

Local/student-scale computer-vision and adaptive traffic-light **simulation** prototype with a FastAPI backend and React/Vite PC Studio frontend.

## Current release state

Root [`VERSION`](VERSION) is authoritative. V032 / `0_3_2` is the current unaccepted candidate. V031 / `0_3_1` is the previous candidate because the owner explicitly requested V032 before separately accepting V031. V024 / `0_2_4` remains the owner-confirmed passed baseline.

V032 adds PC-pull ESP32-CAM integration for the stock Arduino CameraWebServer example. The user enters the ESP private-LAN IP in PC Studio; the PC pulls `/capture` frames into the existing processing pipeline and can show the ESP `:81/stream` preview.

## Documentation entry points

| Need | Read |
| --- | --- |
| Current candidate | `VERSION`, [`docs/START_HERE.md`](docs/START_HERE.md) |
| Current patch | [`docs/PATCH_0_3_2.md`](docs/PATCH_0_3_2.md) |
| Hardware camera | [`docs/ESP32_CAMERA_STREAMING.md`](docs/ESP32_CAMERA_STREAMING.md) |
| Scope | [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) |
| API | [`docs/API_CONTRACTS.md`](docs/API_CONTRACTS.md) |
| Agent rules | [`AGENTS.md`](AGENTS.md) |

## Implemented prototype functions

- receive/simulate camera frames;
- V032 private-LAN ESP32-CAM pull using stock CameraWebServer `/capture`, with direct `:81/stream` preview;
- legacy raw JPEG/PNG device-frame upload;
- local trained-model inference;
- dataset capture/delete/review/manual labeling and managed YOLO training;
- model registry/load/default/delete;
- camera-aligned traffic zones and counting lines;
- sampled occupancy + lightweight track-derived flow analytics;
- configurable protected simulated signal timing;
- ranked adaptive scenarios using controller metrics or zone/class counts;
- deterministic one-winner arbitration with bounded timing/protected phase order;
- persistent signal decision history;
- isolated seeded single-junction and network simulation experiments;
- synthetic two-intersection cooperation, pedestrian-aware, class-aware and emergency-priority comparison modes;
- persistent normalized decision evidence for network experiments.

## Important semantics

- Occupancy is sampled presence, not throughput.
- Flow comes from prototype track/line/region events.
- Zone/class counts are per-frame observations.
- Network experiment evidence is synthetic simulation evidence.
- V032 ESP frames are real camera input, but they do not by themselves prove detector accuracy or public-road control capability.
- Manual/synthetic inputs remain labeled with provenance.

## Safety scope

AiTL is for local simulation, classroom/model-junction work, computer-vision experiments, and supervised prototype testing. It does not send commands to physical/public-road traffic infrastructure.
