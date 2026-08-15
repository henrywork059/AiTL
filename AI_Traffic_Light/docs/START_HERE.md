# Start Here — Current V020 candidate

The owner-confirmed passed baseline is `0_1_7`. V020 / `0_2_0` is the current candidate.

## Current working path

1. Start the FastAPI PC Studio backend.
2. Start the React/Vite frontend.
3. Use receiver or synthetic-camera frames.
4. Draw and save traffic zones directly over the current camera/simulation image.
5. Inspect the same saved zones and compact simulated signal on Live AI.
6. Capture useful frames; delete unwanted captures when needed.
7. Manually label retained frames and build the managed YOLO dataset.
8. Train locally with convergence monitoring and patience-based early stopping.
9. Load/manage trained models and inspect zone-aware simulation recommendations.
10. Adjust runtime settings and inspect recent backend logs when troubleshooting.

## Still outside the current prototype

- automatic labeling;
- model export/runtime packaging;
- complete device-camera firmware workflow;
- production-grade tracking or multi-camera synchronization;
- direct control of real public-road traffic infrastructure.

Traffic recommendations and the Live AI signal graphic are simulation/display outputs only.
