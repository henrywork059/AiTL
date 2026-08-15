# Start Here — Current V021 candidate

The current candidate is V021 / `0_2_1`, explicitly requested by the owner as the next patch after V020. V020 / `0_2_0` is the previous candidate; the owner-confirmed passed baseline remains V017 / `0_1_7`.

## Current working path

1. Start the FastAPI PC Studio backend.
2. Start the React/Vite frontend.
3. Use receiver or synthetic-camera frames and load a trained model for live detection-backed functions.
4. Draw/save traffic zones and optional analytics-only `counting_region` polygons over the current camera image.
5. Use Live AI for detections, saved-zone overlays, and the simulated traffic signal.
6. Use Traffic Logic for current whole-frame/region occupancy and the simulation-only recommendation.
7. Use Traffic Analytics to inspect vehicle/pedestrian occupancy over time, peaks/averages, region activity, and phase changes; export CSV when useful.
8. Capture/review/label useful frames and build the managed YOLO dataset.
9. Train locally with convergence monitoring and early stopping, then manage/load trained models.
10. Use Settings and Logs for runtime tuning/troubleshooting.

## Traffic analytics interpretation

Traffic history stores sampled object occupancy from detection frames. It does not yet provide unique passage/throughput counts because object tracking across frames is not implemented.

## Still outside the current prototype

- unique cross-frame vehicle/person tracking and passage counting;
- automatic labeling;
- model export/runtime packaging;
- complete device-camera firmware workflow;
- production-grade multi-camera synchronization;
- direct control of real public-road traffic infrastructure.

Traffic recommendations and signal graphics are simulation/display outputs only.
