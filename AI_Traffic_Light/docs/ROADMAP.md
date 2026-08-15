## 0_2_0 — Camera-aligned zones and capture lifecycle

Status: candidate, awaiting owner acceptance.

- Delete unwanted captures with their paired metadata/manual labels.
- Use the live receiver/simulation image as the Zone Editor background.
- Overlay persisted zones on Live AI with reference-to-frame scaling.
- Add a compact simulation-only traffic signal to Live AI.
- Preserve V017 training convergence, early stopping, traffic logic, settings/logs, and model-management behavior.
- Keep physical public-road control outside the project scope.

## 0_1_7 — Convergence monitoring and working prototype tools

Status: passed baseline, owner-confirmed before V020.

- Add live per-epoch training convergence history and a frontend convergence plot.
- Use Ultralytics patience-based automatic early stopping and report stopped-early runs explicitly.
- Replace the main Zone Editor placeholder with persistent polygon editing.
- Replace mock Traffic Logic with live trained-detection zone counting and simulation-only recommendations.
- Replace template Settings with persistent runtime settings and mock Logs with recent real backend records.
- Keep legacy `/api/mock` data only as backward-compatible smoke/offline fixtures, not as the connected-page implementation.
- Keep automatic labeling, model export, finished device firmware, and physical public-road control outside this patch.
