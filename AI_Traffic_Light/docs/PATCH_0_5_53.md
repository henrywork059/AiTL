# Patch 0_5_53 — Read-only camera endurance evidence recorder

Candidate `0_5_53`, previous `0_5_52`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.
Roadmap Update **09 / H05**.

## Implementation and scope

Added `scripts/camera_endurance_benchmark.py`, a reusable, bounded-memory recorder for the **existing** `GET /api/camera/remote/status` API. It polls saved physical cameras by stable source ID, without changing source selection, issuing stream-control commands, opening a JPEG socket, decoding frames or changing traffic signals.

Exports a per-source `samples.csv` and a `summary.json` in a newly created directory, by default under the current user's `~/MESH_camera_endurance/`. Reports source settings/target FPS and changes, original PC-receive frame age, smoothed receiver FPS, intervals, disconnected/stale samples, observed sequence-gap/duplicate/reset and reconnect/session-recovery counter increases, and sampled recovery durations. Backend CPU and resident memory can be captured with optional `psutil` when the correct `--backend-pid` is provided; otherwise resource fields remain null and the limitation is recorded. Missing status polls create error rows. The collector automatically reads VERSION and the Git HEAD when available; missing commit identity remains null rather than invented.

Status responses can combine selected-camera fields during concurrent camera switching; this recorder deliberately reads **only** individually keyed `cameras[]` entries, with a synthetic contradictory-selected-state regression. The underlying selected-status race is not repaired or claimed resolved by this patch.

Sequence gaps are estimates derived from the ESP source sequence, not measured IP packet loss. Counter deltas cannot recover increments between resets and polls. Receiver age is not camera acquisition-to-display latency. A recovery duration is the difference between a sampled disconnection and sampled reconnection, with uncertainty at least the status polling cadence; unclosed outages are censored. The status API's existing low-rate ESP control/status refresh may influence resource measurements. This is a local prototype, not an endurance certification.

## Validation evidence

Actually executed in local Python:
- `python scripts/test_v0553_camera_endurance.py`: PASS (all three deterministic test functions).
- `python -m pytest -q scripts/test_v0553_camera_endurance.py`: 3 passed.
- `python -m compileall -q` on the recorder and focused test: PASS.
- Both pushed source blobs were checksum-matched to the exact locally tested Python files.

Synthetic fixture verifies independent two-camera results despite conflicting top-level selected status, stale/recovery handling, sequence-counter epoch resets, failed polls, CPU/memory fields, output schema, private profile host omission and non-overwriting export behavior. These are **illustrative/synthetic**, not live ESP endurance measurements.

Not executed: complete repository offline suite, full structural checker, Windows acceptance runner, frontend build, live PC Studio HTTP integration, actual ESP session endurance or weak-Wi-Fi/power-loss experiments; CI results not established. Previous candidates remain unaccepted.

## Running an actual benchmark

With PC Studio running and the saved ESP streams already started, from the `AI_Traffic_Light` project directory:

```powershell
python scripts/camera_endurance_benchmark.py --duration-seconds 600 --sample-seconds 1 --environment "ESP32-CAM board/firmware, power, Wi-Fi access point and range; test conditions"
```

Optionally add `--source-id esp32_cam_01`, `--backend-pid <actual-backend-pid>` (requires optional `psutil`) and `--output-dir <new-empty-directory>`. The recorder never starts a camera. Validate the results against raw CSV and report any zero/missing measurements. For long runs, record actual hardware, firmware, radio conditions, power and duration in the environment field. No host/IP is collected automatically, but user-entered environment text is retained. Do not commit evidence logs to the source repository.

Owner acceptance of the **software patch**:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Next roadmap item: Update 10 / H06 — device capability contract. No promotion to baseline, main-branch change or public-road actuation.
