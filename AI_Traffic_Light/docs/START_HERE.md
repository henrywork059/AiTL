# Start Here — Current V017 candidate

The project has moved beyond the original mock/template skeleton. The current passed baseline remains `0_1_5`; V016 and this V017 patch remain candidates until owner acceptance.

## Current working path

1. Start the FastAPI PC Studio backend.
2. Start the React/Vite frontend.
3. Use receiver or synthetic-camera frames.
4. Capture and manually label useful frames.
5. Build the managed YOLO dataset.
6. Train locally and monitor validation convergence; patience-based early stopping can end a converged run before the maximum epoch count.
7. Load a trained model in Live AI.
8. Edit persistent zones and inspect live detection-centre counts in Traffic Logic.
9. Adjust runtime settings and inspect recent backend logs when troubleshooting.

## Still outside the current prototype

- automatic labeling;
- model export/runtime packaging;
- complete device-camera firmware workflow;
- production-grade tracking or multi-camera synchronization;
- direct control of real public-road traffic infrastructure.

The traffic recommendation pages are for simulation, demonstration, classroom testing, and human-supervised analysis only.
