# V015 acceptance checklist

1. Health and Dashboard show `0_1_5`.
2. At least two local trained models are present under `outputs/training/*/weights/best.pt`.
3. Live AI shows a model selector with discovered runs.
4. Loading a selected model changes the active model ID.
5. Setting a default model persists after a backend restart.
6. Deleting a selected model removes its run directory and updates the list.
7. Live detections still work after selecting a model.
8. Lowering confidence to 1–10% affects returned/visible detections.
9. Boxes and labels can be toggled independently.
10. Class visibility filters update the overlay and result table.
11. The Models page supports refresh, load, set-default, and delete.
