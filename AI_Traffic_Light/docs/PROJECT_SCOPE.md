# Project Scope and Capability Status

This document records what AiTL is intended to demonstrate and how capability claims should be worded. Root `VERSION` owns release state.

## Scope vocabulary

- **Implemented** — active, testable code path.
- **Foundation** — supporting schema/service/context exists but target behavior is inactive.
- **Simulation-only** — implemented only in local synthetic/test behavior.
- **Planned** — intended but not sufficiently implemented.
- **Out of scope** — deliberately excluded.

## Implemented prototype families

- physical ESP32-CAM image input over a private LAN using stock Arduino CameraWebServer `/capture` plus Camera Sources preview;
- legacy raw device-frame receiver and signal-aware synthetic camera;
- local trained-model inference;
- dataset capture/review/manual labeling/managed YOLO training;
- camera-aligned zones/counting lines;
- sampled occupancy and lightweight track-derived flow;
- configurable protected simulated signal timing and ranked scenarios;
- isolated Fixed-vs-Adaptive single-junction experiments;
- generic intersection/topology/source identity;
- isolated deterministic two-intersection synthetic transfer/cooperation experiments;
- simulation-only pedestrian-aware, class-aware and emergency-priority network modes;
- normalized persistent network-experiment decision evidence;
- structured live decision/explanation foundation.

## Physical ESP status

**Status: physical camera input implemented; physical signal output planned/outside the current candidate.**

V032 establishes a real camera transport boundary:

```text
ESP32-CAM / OV2640
→ stock Arduino CameraWebServer
→ PC pulls JPEG snapshots
→ existing CameraFrameService
→ PC-side inference / capture / zones / analytics
```

This supports a controlled model-junction demonstration using real camera images. It does **not** mean:
- ESP-side AI inference;
- independent simultaneous multi-camera frame retention;
- physical signal LED/controller output;
- public-road traffic authority.

## Multi-intersection cooperation

**Status: bounded two-intersection cooperation implemented in isolated simulation; broader/live cooperation planned.**

Separate intersection controllers, synthetic configured-link transfer, predicted arrivals and bounded downstream timing changes are implemented for the isolated benchmark. Live camera links remain source/topology input, not proof of observed cross-camera transfer or live cooperation.

## Emergency priority

**Status: simulation-only configured emergency priority implemented; compatible live-perception evidence planned.**

Emergency lifecycle/priority is an explicit simulator event with no detector-confidence claim. Physical camera input added by V032 does not automatically make emergency recognition live.

## Pedestrian-aware control

**Status: simulation-only request/starvation/clearance behavior implemented; stronger live evidence planned.**

Per-frame person detections/occupancy must not be described as unique pedestrian throughput or reliable individual wait time unless tracking evidence supports it.

## Different vehicle classes

**Status: simulation-only class-rich demand and bounded class-aware control implemented; live class evidence strengthening planned.**

Synthetic profiles and weights are not detector-accuracy evidence. Real V032 camera frames can be classified only by the loaded PC model and must retain detector provenance.

## Explainable decisions

**Status: persistent normalized network-experiment evidence implemented; universal live audit strengthening planned.**

V031 decision evidence remains non-controlling. V032 changes camera input transport only.

## Evidence hierarchy

Prefer:
1. deterministic unit/service regression;
2. API integration;
3. seeded simulator comparison;
4. owner PC Studio acceptance;
5. controlled physical model demonstration.

## Out of scope

- direct public-road signal control;
- traffic-cabinet/pre-emption integration;
- bypassing safety systems;
- autonomous public-road authority;
- safety certification;
- claiming unsupported perception capability.
