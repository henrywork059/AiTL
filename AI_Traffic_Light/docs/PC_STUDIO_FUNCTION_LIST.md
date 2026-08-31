# PC Studio Function List

This durable catalog describes implemented PC Studio capabilities without owning the current release number. Use root `VERSION` and `START_HERE.md` for candidate state.

## Camera

- private-LAN ESP status/control connection with Connect transferring zero image bytes;
- PC-owned OV2640 settings and target FPS;
- persistent length-prefixed binary TCP JPEG transport from each ESP on port 81;
- fixed 16-byte `ATL1` header carrying JPEG length, sequence and ESP uptime;
- exact fixed-length PC reads with JPEG validation;
- production PSRAM capture path using one framebuffer + `CAMERA_GRAB_LATEST`;
- tuned production sender retaining TCP keepalive / `TCP_NODELAY` / bounded progress and using larger plain application writes while preserving the existing `ATL1` wire contract;
- configured JPEG quality/resolution stay fixed across transport pressure unless the user changes saved settings;
- automatic ESP session recovery after reboot/loss;
- serialized/retried low-rate ESP HTTP control requests;
- reconnect/FPS/sequence-gap/send/RSSI/BSSID/channel telemetry;
- up to the configured maximum persisted ESP camera profiles with IP/FPS/OV2640 settings;
- independent background TCP workers and newest-frame cache per connected ESP;
- one explicitly selected ESP feeds the shared Live AI / Dataset Capture / zones / analytics pipeline;
- freshness-guarded switching so stale caches, retired sessions and old-IP frames cannot replace the selected source;
- simulation pause/resume across physical ESP streams;
- backend shutdown disconnects active ESP sessions;
- legacy raw JPEG/PNG upload compatibility;
- browser preview remains the backend MJPEG relay rather than opening additional browser→ESP streams.

Several ESP streams may exist at once, but this is **multi-camera input/session support**, not simultaneous independent inference for every camera.

## Junction Network

- editable PC Studio page representing installed/model junctions as logical draggable nodes;
- directed lines reuse persisted intersection-network topology links;
- add/remove/rename/enable junctions and edit link travel-time/enabled state;
- assign several saved ESP camera source IDs to one junction;
- one source ID remains exclusive to one junction for unambiguous mapping;
- choose an optional primary source for each junction;
- persist logical node positions, source assignments and topology through the existing `config/intersections.json` service;
- show saved ESP reachability/streaming/FPS/error state per junction;
- show current vehicle/pedestrian load, phase/decision and supported event/warning context for the junction resolved from the shared selected source;
- explicitly show unavailable traffic observations for junctions not currently observed by the shared live/simulation pipeline;
- use `GET /api/traffic/network/overview` as a read-only projection rather than creating a parallel controller or camera registry.

The Junction Network page does not implement simultaneous multi-junction inference, cross-camera identity/transfer matching, live emergency recognition or physical/public-road signal control.

## Camera Diagnostics

The Camera Test page provides a one-button diagnostic for the selected saved ESP. Depending on the flashed diagnostic firmware, one run can measure/control:

- direct `/status` control reachability and latency;
- AiTL camera/stream protocol compatibility and camera readiness;
- RSSI, BSSID and Wi-Fi channel telemetry;
- direct camera transport bypassing the normal PC Studio stream worker;
- direct receiving while control polling runs concurrently;
- normal `RemoteCameraManager` / `RemoteCameraService` managed stream behavior;
- send-failure/deadline telemetry and state restoration;
- architecture/tuning experiments for framebuffer/grab mode, requested FPS, JPEG quality, TCP write size, transfer size and repeatability when the matching diagnostic firmware is flashed.

Diagnostic evidence is comparative prototype evidence. It does not automatically change the production transport or certify camera/network reliability.

## Live AI, zones and traffic

- load a selected/default locally trained detector;
- run inference on the selected camera or built-in simulation frame;
- confidence/class/box/label visibility controls;
- camera-aligned traffic zones and counting lines;
- prototype cross-frame tracking and flow events;
- sampled occupancy and region analytics;
- ranked simulated signal scenarios with protected timing bounds;
- explanation context and decision history/evidence surfaces;
- isolated deterministic single-junction and network simulation experiments with their documented synthetic provenance.

## Dataset and models

- capture selected receiver/simulation frames with metadata;
- review/delete captures and manually draw YOLO labels;
- build a managed train/validation YOLO dataset;
- run local Ultralytics training with convergence telemetry and early stopping;
- discover/load/default/delete local trained-model runs.

Model export remains a later capability unless the current source/contract explicitly implements it.

## Scope boundary

Multiple ESP image streams, Junction Network configuration, simulated network experiments and diagnostic results do **not** imply multiple simultaneous independent live signal controllers, validated detector reliability, ESP-side inference, certified control authority or physical/public-road traffic-signal actuation.
