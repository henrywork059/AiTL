# V020 acceptance checklist

V020 remains a candidate until the project owner explicitly confirms the required checks.

1. Health, Dashboard Project stage, sidebar/version label, and template status report `0_2_0`.
2. V017 remains the recorded passed baseline (`0_1_7`).
3. Existing V016/V017 camera simulation, training convergence, early stopping, settings, logs, traffic logic, labeling, and model-management functions show no regression.
4. Zone Editor displays the current receiver or simulation camera frame rather than the old drawn reference background.
5. Zone click coordinates stay aligned with the camera image and save through the existing 1280×720 reference coordinate system.
6. Saved zones persist across page navigation/backend requests.
7. Live AI overlays persisted zone polygons over real receiver/simulation camera frames.
8. Zone overlays scale correctly if the active camera resolution differs from 1280×720.
9. Live AI **Show zones** toggle hides/shows zones without changing inference results.
10. A compact traffic signal appears at the top-right of the Live AI canvas.
11. The compact signal reflects the current simulation-only phase and does not imply physical traffic control.
12. Dataset Capture can delete the latest saved capture after confirmation.
13. Dataset Review can delete the selected saved capture after confirmation.
14. Deleting a capture removes its image file, paired metadata JSON, and saved manual-label JSON when present.
15. Deleted captures disappear from the review list and capture counts update.
16. Deleting a capture used by an existing managed YOLO build makes that build stale until rebuilt.
17. Re-deleting a missing capture returns `ATL-DATASET-003`; filesystem deletion failures use `ATL-DATASET-007`.
18. Delete responses preserve the standard JSON envelope, request ID, and backend logging.
19. Python/service/API checks, frontend typecheck/build, structure check, and `git diff --check` pass locally.
20. Live detections/traffic recommendations remain disconnected from physical public-road traffic signals.
