# PC Studio Function List

This is a current capability catalog. Read root `VERSION` for candidate state and `PROJECT_SCOPE.md` for scope boundaries.

## Camera / live simulation

- receive raw JPEG/PNG device uploads;
- V032 connect to a stock Arduino ESP32-CAM CameraWebServer by private-LAN IPv4;
- probe/pull `/capture` JPEG snapshots into the common PC frame pipeline;
- direct `:81/stream` Camera Sources preview with backend-frame fallback;
- remote connection/fetch telemetry and reconnect/disconnect;
- pause remote ingestion while built-in simulation is active and resume afterward;
- signal-aware synthetic single-junction scene with density and pause/resume controls.

## Inference / dataset / training

- local trained-model inference on the common current camera frame;
- capture/delete/review/manual-label frames;
- managed YOLO train/validation dataset;
- local Ultralytics training with convergence/early stopping;
- model registry/load/default/delete.

## Zones / analytics

- camera-aligned waiting/crossing/queue/counting/ignore regions and counting lines;
- sampled occupancy history;
- lightweight tracking;
- directional line passages and region entry/exit/dwell;
- separate occupancy and flow analytics with CSV export.

## Traffic logic

- protected phase base/min/max timing;
- Fixed/Adaptive/Test modes;
- ranked ALL/ANY scenarios using metrics or zone/class counts;
- bounded extend/reduce/hold/request-next/incident actions;
- one highest-ranked eligible winner;
- persistence/cooldown/stale fallback;
- decision history/explanations.

## Simulation Lab / network evidence

- isolated Fixed-vs-Adaptive single-junction experiments;
- isolated two-intersection seeded network experiments;
- Fixed, Independent Adaptive, Cooperative, Pedestrian-aware, Class-aware, Emergency Baseline and Emergency-priority comparison modes;
- synthetic transfer/predicted-arrival/cooperation evidence;
- pedestrian request/clearance evidence;
- synthetic class profiles/per-class metrics;
- configured simulated emergency lifecycle/priority evidence;
- normalized persistent decision evidence JSON/CSV.

## Network / explanation foundation

- generic intersection/source identity;
- directed neighbour links;
- live neighbour/decision context;
- explicit provenance and inactive live-cooperation/public-road-control boundaries.

## V032 limitation

The backend still keeps one latest non-simulation frame rather than simultaneous independent frame buffers for many ESP cameras. V032 establishes the physical camera input path; multi-camera live routing is a later extension.

## Safety

Physical ESP camera input is implemented. Physical/public-road signal control is not.
