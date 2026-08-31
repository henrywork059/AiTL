# Start Here — V0311

V0311 / `0_3_11` is the current unaccepted candidate. V0310 / `0_3_10` is the previous candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline.

## Normal Windows workflow

For routine update, validation and launch, use the same command from any PowerShell working directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The idempotent restart behavior remains: the helper may stop listeners on 8000/5173 only when Win32 process evidence identifies them as this repository's AiTL PC Studio process tree. Unrelated listeners are protected. Runtime/user data is preserved.

## V0311 Junction Network

Open **Traffic → Junction Network** to configure and visualize the prototype junction installation model.

The page uses the established `config/intersections.json` network configuration:

```text
junction node
├─ label / enabled state / signal profile
├─ persisted canvas position
├─ 0..N assigned source_ids
├─ optional primary_source_id
└─ directed topology links to other junctions
```

One junction may contain multiple saved ESP cameras. One camera/source id may belong to only one junction so a received frame still resolves to one unambiguous junction.

The page shows:

- draggable junction nodes and directed topology lines;
- assigned-camera health and measured FPS;
- vehicle and pedestrian load for the currently observed junction;
- current prototype phase/decision context;
- ranked-scenario, pedestrian-service and manual/test event indicators when available;
- camera/source and observation warnings.

## Live-data boundary

V0311 does not yet create one AI pipeline for every junction. Several ESP stream workers may exist, but exactly one selected physical/simulation source still feeds the shared inference/traffic pipeline.

Therefore only the junction resolved from the current selected source may show current AI/simulation traffic metrics. Other junctions deliberately show occupancy/load as unavailable while still showing their topology and camera-health state. Do not interpret camera assignment or configured links as live cross-camera fusion, observed vehicle transfer, cooperative signal control, or emergency recognition.

## V0310 camera transport remains active

The production ESP camera path remains the V0310 R10-tuned transport:

```text
PC Connect -> ESP /status only
PC Start -> /config -> /start -> persistent TCP :81
ESP camera -> FB1 / CAMERA_GRAB_LATEST on PSRAM
ATL1 header + configured JPEG -> bounded plain send() writes, max 11680 B/write
selected ESP -> CameraFrameService -> preview / Live AI / capture / zones / analytics
```

For production-camera testing, continue to flash:

```text
apps/device-camera/esp32-cam/arduino/AiTL_ESP32_CAM_V0310/AiTL_ESP32_CAM_V0310.ino
```

V0311 does not require a new ESP firmware sketch because this patch changes PC-side junction configuration/visualization only.

## V0311 acceptance focus

After the normal one-command workflow passes:

1. Open Junction Network.
2. Add/arrange several junctions.
3. Assign multiple saved ESP cameras to one junction.
4. Add at least one directed link and save.
5. Restart PC Studio and verify layout/link/camera assignment persistence.
6. Stream one selected ESP and verify only its resolved junction receives live traffic/pedestrian data.
7. Verify another unselected junction remains explicitly unavailable rather than mirroring the selected junction's counts.
8. Exercise an offline camera warning and an existing simulation/test event.

AiTL remains a local/student-scale prototype; physical/public-road traffic-signal authority is out of scope.
