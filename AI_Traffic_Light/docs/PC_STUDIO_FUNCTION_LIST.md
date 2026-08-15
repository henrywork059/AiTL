# PC Studio Function List (V022 implemented highlights)

## Camera / simulation
- receive JPEG/PNG device frames;
- signal-aware synthetic scene with vehicle stop-line queues and pedestrian curb/WALK behavior;
- Light / Normal / Busy density;
- pause/resume synthetic motion and signal timing.

## Dataset / training
- capture latest frame with metadata;
- delete capture image + metadata + saved labels;
- manual bounding-box labeling;
- managed YOLO train/validation build;
- local Ultralytics training;
- convergence plot and patience-based early stopping.

## Inference / models
- discover/load/default/delete trained models;
- live detections on receiver/simulation frames;
- confidence and visibility controls;
- saved zone/line overlays;
- V022 class-aware cross-frame prototype track IDs shown beside Live AI detections.

## Zones / traffic simulation
- edit/persist camera-aligned waiting, crossing, queue, counting-region, ignore polygons;
- create analytics-only `counting_line` geometry with exactly two distinct points;
- count whole-frame and per-region pedestrian/vehicle occupancy;
- simulation-only phase recommendations plus signal-aware simulator phase display.

## Occupancy analytics
- timestamped bounded occupancy history under `outputs/traffic_history/`;
- whole-frame or polygon-region time series;
- average/peak/busiest-region and phase-change summaries;
- CSV export and explicit occupancy-history clear.

## V022 tracking / flow analytics
- frame-deduplicated stable prototype track IDs;
- one unique directional passage event per track/counting-line pair;
- `left_to_right`, `right_to_left`, `top_to_bottom`, `bottom_to_top` direction;
- region entry/exit events;
- completed region dwell duration;
- average pedestrian waiting-zone dwell;
- persistent bounded events under `outputs/traffic_flow/`;
- time, line, region, and class filtering;
- per-minute passage or region-event plots;
- recent event table;
- CSV export and explicit flow-history clear;
- active tracking status API.

## System / development integrity
- persistent runtime confidence/polling/training-patience/log-level settings;
- recent backend logs with request IDs/error codes;
- canonical root `VERSION` metadata;
- repository/version and patch-ZIP validation;
- runtime datasets/models/occupancy history/flow events excluded from source patches.

## Tracker limitation

The current tracker uses lightweight centroid/IoU association. It can lose or swap IDs during occlusion, large inter-frame motion, long detection gaps, or crowded same-class crossings. Unique passage therefore means a recorded track/counting-line event in this prototype, not certified traffic measurement.

## Still later
- stronger tracking/motion prediction and quality diagnostics;
- model evaluation/validation reporting and model comparison;
- configurable simulation scenario lab;
- automatic labeling;
- model export/runtime package;
- physical public-road traffic control (explicitly outside scope).
