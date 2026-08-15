# V020 acceptance checklist

V020 / `0_2_0` remains a candidate until the project owner explicitly confirms the required checks. Automated tests do not promote `passed_baseline`.

## Release/instruction integrity

1. `VERSION` reports `version: 0_2_0`, candidate status, `previous_version: 0_1_7`, and `passed_baseline: 0_1_7`.
2. `python scripts/check_structure.py` passes in the complete repository.
3. Backend FastAPI, health, smoke, and template version surfaces all derive/report `0_2_0` consistently.
4. Dashboard Project stage, sidebar/version label, and frontend fallback version surfaces report `0_2_0`.
5. `AGENTS.md`, `docs/AI_AGENT_GUIDE.md`, and `docs/AI_AGENT_CHECKLIST.md` describe the candidate/baseline gate and runtime-data preservation rules.
6. The final ZIP passes `scripts/validate_patch_zip.py`, contains only intended changed files, and has no runtime/generated/model content.

## Existing V020 feature checks

7. Existing V016/V017 camera simulation, training convergence, early stopping, settings, logs, traffic logic, labeling, and model-management functions show no regression.
8. Zone Editor displays the current receiver or simulation camera frame rather than the old drawn reference background.
9. Zone click coordinates stay aligned with the camera image and save through the existing 1280×720 reference coordinate system.
10. Saved zones persist across page navigation/backend requests.
11. Live AI overlays persisted zone polygons over real receiver/simulation camera frames.
12. Zone overlays scale correctly if the active camera resolution differs from 1280×720.
13. Live AI **Show zones** toggle hides/shows zones without changing inference results.
14. A compact traffic signal appears at the top-right of the Live AI canvas.
15. The compact signal reflects the current simulation-only phase and does not imply physical traffic control.
16. Dataset Capture can delete the latest saved capture after confirmation.
17. Dataset Review can delete the selected saved capture after confirmation.
18. Deleting a capture removes its image file, paired metadata JSON, and saved manual-label JSON when present.
19. Deleted captures disappear from the review list and capture counts update.
20. Deleting a capture used by an existing managed YOLO build makes that build stale until rebuilt.
21. Re-deleting a missing capture returns `ATL-DATASET-003`; filesystem deletion failures use `ATL-DATASET-007`.
22. Delete responses preserve the standard JSON envelope, request ID, and backend logging.

## Validation and safety

23. Python compile checks and relevant backend service/API/regression tests pass locally using the backend `.venv`.
24. `scripts/test_backend_smoke.py` confirms `meta.request_id` and root-version agreement for version endpoints.
25. Frontend `npm run typecheck` and `npm run build` pass.
26. `git diff --check` passes in the complete repository.
27. The intended changed-file manifest matches the ZIP manifest and SHA-256 is recorded.
28. Live detections/traffic recommendations remain disconnected from physical public-road traffic signals.
29. The owner completes UI/manual checks and explicitly says V020 passed before `passed_baseline` is changed to `0_2_0`.
