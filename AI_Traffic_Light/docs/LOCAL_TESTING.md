# Local Testing Notes (V015)

## Key manual tests

1. Train at least one model so `outputs/training/<run_id>/weights/best.pt` exists.
2. Open **Live AI** and confirm the model list appears.
3. Choose a model and click **Load selected model**.
4. Set a default model and refresh the page; Live AI should auto-load the default when possible.
5. Delete a non-default model and confirm its run directory is removed from disk.
6. Lower confidence to 1–10% and confirm the backend still responds.
7. Toggle boxes, labels, and class filters on the live overlay.
8. Open **Models** and repeat load/default/delete actions there.
