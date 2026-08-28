# V032 Acceptance Checklist

V032 / `0_3_2` is the current unaccepted candidate. V031 / `0_3_1` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Release / packaging

1. `VERSION` reports `0_3_2`, previous `0_3_1`, passed baseline `0_2_4`, and candidate status.
2. `docs/PATCH_0_3_2.md`, `CHANGELOG.md`, `START_HERE.md`, camera/API docs and version surfaces agree.
3. Changed-files ZIP contains only `AI_Traffic_Light/` paths and no runtime/generated content.
4. ZIP integrity/path validation and manifest/hash checks pass.

## Focused remote-camera behavior

5. `scripts/test_remote_camera_pull.py` passes.
6. RFC1918 literal IPv4 addresses are accepted.
7. Public IPs, hostnames, loopback/link-local/non-IPv4 targets are rejected.
8. Connect probes stock CameraWebServer `/capture` before starting the worker.
9. A valid JPEG enters the existing CameraFrameService with the requested source ID.
10. Remote status exposes host/source/capture/stream URLs, worker state, counters and last error/status.
11. Background pulls do not overlap through multiple worker instances after reconnect/disconnect.
12. Disconnect stops the worker and does not delete the last camera frame.
13. FastAPI shutdown stops the worker.

## Simulation coexistence

14. Starting Camera Sources simulation pauses remote ingestion.
15. Remote configuration remains present during simulation.
16. Stopping simulation resumes ESP ingestion without reconnecting.
17. Existing Light/Normal/Busy and pause/resume simulation controls still work.

## Backward compatibility / shared pipeline

18. Legacy raw `POST /api/camera/frame` still accepts valid JPEG/PNG.
19. `GET /api/camera/frame` still returns the common latest frame with request/source/frame headers.
20. Live AI can use the remote ESP frame through the existing inference source path.
21. Dataset Capture can persist a remote ESP frame.
22. Zone Editor/current-frame overlays remain aligned with physical-camera frames.
23. Occupancy/tracking/flow continue to consume inference outputs with unchanged semantics.

## Frontend

24. Camera Sources provides ESP address and source ID fields.
25. Connect/Reconnect/Disconnect mutation failures are visible to the user.
26. Connected state shows remote health/counters.
27. Direct `:81/stream` preview is used when available.
28. If direct MJPEG cannot render, the page falls back to the backend latest-frame image.
29. Remote status polling is serial/non-overlapping.

## Physical ESP32-CAM

30. Stock Arduino CameraWebServer uploads/runs on the OV2640 ESP32-CAM.
31. `/capture` returns a real photograph.
32. `:81/stream` displays live MJPEG.
33. Entering that ESP IP in PC Studio connects successfully.
34. Remote fetch counters continue increasing.
35. Live AI shows the physical camera image.
36. Dataset Capture saves a physical-camera image.
37. Simulation takeover/resume works on the real device connection.

## Inherited validation

38. Python compile passes on the complete checkout.
39. All non-live regression scripts pass.
40. `scripts/check_structure.py` passes.
41. Frontend `npm ci`, `npm run typecheck`, and `npm run build` pass.
42. Live `test_backend_smoke.py` passes and reports `0_3_2`.
43. `git diff --check` passes.
44. Existing V027–V031 network/cooperation/pedestrian/class/emergency/evidence behavior shows no regression.

## Claims / safety

45. V032 is described as physical camera **input**, not public-road traffic control.
46. No ESP-side detector accuracy is claimed; inference remains PC-side.
47. No physical traffic-light LED/signal command path is introduced.
48. Multi-camera independent live frame storage is not claimed.
49. Owner explicitly confirms V032 passed before `passed_baseline` changes.
