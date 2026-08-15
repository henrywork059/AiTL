
## 0_1_7 — Convergence monitoring and working prototype tools

Status: candidate, awaiting owner acceptance.

- Add live per-epoch training convergence history and a frontend convergence plot.
- Use Ultralytics patience-based automatic early stopping and report stopped-early runs explicitly.
- Replace the main Zone Editor placeholder with persistent polygon editing.
- Replace mock Traffic Logic with live trained-detection zone counting and simulation-only recommendations.
- Replace template Settings with persistent runtime settings and mock Logs with recent real backend records.
- Keep legacy `/api/mock` data only as backward-compatible smoke/offline fixtures, not as the connected-page implementation.
- Keep automatic labeling, model export, finished device firmware, and physical public-road control outside this patch.
