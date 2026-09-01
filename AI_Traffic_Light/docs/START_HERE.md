# Start Here — V0311

V0311 / `0_3_11` is the current owner-confirmed passed baseline as of 2026-09-01. V0310 / `0_3_10` is the previous candidate.

## Normal Windows workflow

For routine update, validation and launch, use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The helper safely fast-forwards `main`, reloads itself, runs the automatic validation suite, replaces only AiTL-owned PC Studio listeners on ports 8000/5173, runs live smoke and opens PC Studio. Runtime/user data is preserved and unrelated port owners are protected.

Repeated runs are dependency-aware: unchanged backend/frontend dependency manifests skip redundant `pip install` / `npm ci`, while regressions, frontend typecheck/build, Git cleanliness and live smoke still run. Use `-RefreshDependencies` only when you intentionally need to force dependency refresh.

For future development, read root `VERSION` and `AGENTS.md`, then use `docs/PATCH_PLAYBOOK.md` as the short execution path.

## V0311 Junction Network

Open **Traffic → Junction Network** to configure and visualize the prototype junction installation model.

```text
junction node
├─ label / enabled state / signal profile
├─ persisted canvas position
├─ 0..N assigned source_ids
├─ optional primary_source_id
└─ directed topology links to other junctions
```

One junction may contain multiple saved ESP cameras. One camera/source id may belong to only one junction so a received frame resolves to one unambiguous junction.

The page shows draggable junction nodes and directed links, camera health/FPS, vehicle and pedestrian load for the currently observed junction, prototype phase/decision context, event indicators and warnings.

## Live-data boundary

V0311 does not create one AI pipeline for every junction. Several ESP stream workers may exist, but exactly one selected physical/simulation source still feeds the shared inference/traffic pipeline. Other junctions intentionally show live occupancy/load as unavailable rather than copying the selected junction's data.

Camera assignment or configured links do not imply live cross-camera fusion, observed transfer, cooperative signal control or emergency recognition.

## Production camera firmware

V0311 keeps the V0310 R10-tuned production camera transport:

```text
ESP camera -> FB1 / CAMERA_GRAB_LATEST on PSRAM
ATL1 header + configured JPEG -> bounded plain send() writes, max 11680 B/write
selected ESP -> CameraFrameService -> preview / Live AI / capture / zones / analytics
```

Continue to flash:

```text
apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino
```

## Passed-state note

The owner confirmed V0311 is running correctly and passes on 2026-09-01. Future normal patch development therefore starts from `0_3_11` as the passed baseline. Increment only when the owner explicitly requests the next patch/version.

AiTL remains a local/student-scale prototype; physical/public-road traffic-signal authority is out of scope.
