# Roadmap

Root `VERSION` defines the active candidate. This roadmap records dependency order, not acceptance state.

## Current V032 milestone — physical camera input

V032 closes the first hardware-input gap by letting PC Studio connect to the already-working stock Arduino ESP32 CameraWebServer using the ESP private-LAN IP.

Implemented milestone:

```text
physical OV2640 image
→ ESP32-CAM Wi-Fi server
→ PC-side camera transport
→ common frame pipeline
→ inference / capture / zones / analytics
```

This is camera input only.

## Priority 1 — accept and harden V032

- complete full backend/frontend regression;
- physical ESP reconnect/simulation/capture acceptance;
- confirm frame rate/resolution is practical for the model junction;
- retain clean errors for unreachable/restarted ESP devices.

## Priority 2 — independent multi-camera live sources

Before claiming a physical multi-intersection system:

- retain latest frame independently per source/intersection;
- explicit source selection/routing for inference, capture and zone pipelines;
- camera health per node;
- avoid cross-source tracker identity contamination;
- preserve provenance and stale-source fallback.

## Priority 3 — model-junction signal output abstraction

For classroom/model hardware only, add an isolated device-output interface so simulated/controller state can drive model LEDs without coupling signal logic to ESP-specific code.

This must remain separate from public-road traffic infrastructure and preserve controller safety semantics.

## Priority 4 — network orchestration generalization

- multiple simultaneous directed links/intersections;
- generic N-intersection run selection;
- richer arrival prediction/uncertainty;
- network/corridor objectives;
- multi-link emergency/class context;
- keep normalized evidence generic.

## Priority 5 — compact network/evidence UI

- topology/run setup;
- per-mode/per-intersection summaries;
- pairwise comparisons;
- normalized evidence filters and drill-down;
- clear synthetic vs physical-input provenance.

## Priority 6 — live-evidence strengthening

Only when compatible trained perception exists:

- evaluate class/pedestrian detection on real camera data;
- reliable live wait/flow reconstruction;
- emergency recognition only with an actual validated source;
- confidence/uncertainty and failure-state evidence.

## Outside scope

Physical/public-road cabinet control, bypassing road safety systems, production autonomous authority and safety certification remain excluded.
