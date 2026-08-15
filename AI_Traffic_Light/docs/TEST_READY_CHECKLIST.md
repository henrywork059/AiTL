# V017 acceptance checklist

V017 remains a candidate until the project owner explicitly confirms every required item.

1. Health, Dashboard Project stage, sidebar/version label, and template status report `0_1_7` with no stale `0_1_5` / `0_1_6` project-stage text.
2. Existing V016 camera simulation still supports vertical pedestrian travel, horizontal vehicles, Light/Normal/Busy density, and Pause/Resume.
3. Train / Export accepts an Early-stop patience value and sends it to the backend.
4. Training status adds one convergence-history point per completed train+validation epoch.
5. The convergence plot visibly updates during a real local training run.
6. Best fitness, best epoch, and no-improvement/patience counters update coherently.
7. A deliberately plateauing/long-enough run stops before maximum epochs when Ultralytics patience is exhausted and status becomes `early_stopped`.
8. An early-stopped run still produces/discovers its best model when Ultralytics created `best.pt`.
9. Zone Editor loads editable reference zones and supports polygon point editing.
10. Apply draft + Save zones persists the configuration across navigation/backend requests.
11. Invalid zone geometry is rejected with the standard API error envelope and stable `ATL-ZONE-*` code.
12. Reset defaults restores the simulation-aligned pedestrian/crossing/vehicle queue zones.
13. Traffic Logic uses the current trained-model frame when a model/camera frame is available.
14. Person detections in waiting/crossing zones and vehicle detections in queue zones update the displayed counts.
15. Traffic Logic provides a reasoned simulation-only phase recommendation and evaluated frame number.
16. Traffic Logic remains disconnected from physical/public-road traffic signals.
17. Settings page persists default confidence, camera-status poll interval, training patience, and log level.
18. Saved log level changes backend logging level without restarting.
19. Logs page shows actual recent backend records rather than fixed mock messages.
20. Real log records can expose request IDs and stable error codes when those fields are present.
21. All main PC Studio pages are listed as `test-ready`; Model Export remains explicitly later/not implemented rather than falsely marked complete.
22. Existing capture, manual labeling, managed YOLO build, model selection/default/delete, live inference, 1% confidence, box/label toggles, and class filters still work.
23. Python/service/API checks, frontend typecheck/build, structure check, and `git diff --check` pass locally.
