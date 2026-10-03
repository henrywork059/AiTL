# Local Testing — V0315

Expected release state:

```text
version: 0_3_15
previous_version: 0_3_14
passed_baseline: 0_3_11
status: concurrency hardening and conflict cleanup candidate
```

## Normal run

```powershell
& "C:\Users\henry_sik0ar\Downloads\AiTL_app\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Expected sequence remains:

```text
fast-forward main
→ reload runner once
→ Python compile
→ structure/release consistency
→ runner regression
→ automatic offline regressions
→ frontend typecheck/build
→ Git cleanliness
→ safe AiTL process replacement
→ live backend smoke
→ launch PC Studio
```

## V0315 focused checks

- `test_frontend_polling_structure.py`: single-flight hook, controller usage and mutation serialization.
- `check_structure.py`: shared polling ownership and no `window.setInterval` in frontend TypeScript.
- Existing firmware regression: confirms PlatformIO compiles only V0310 wrapper while retaining the required V037 implementation.
- Existing camera, signal, network, dataset, training, inference and persistence regressions remain unchanged.

## Manual stress checks

1. **Logs:** click Refresh repeatedly around automatic refresh; UI should not create parallel fetches.
2. **Traffic Analytics:** change mode/window/scope/class rapidly, then clear history; old data must not reappear after clear.
3. **Dataset Capture:** capture/delete near a scheduled status refresh; final counts and last-capture state must be correct.
4. **Train / Export:** start training near a status poll; the returned running state must not be overwritten by an older idle response.
5. **Live AI:** change confidence/model/camera availability; detections should continue without duplicate timer loops.
6. **Camera Sources:** switch simulation/physical mode near a status refresh; final mode/status must match the requested transition.

No ESP reflash is required.

`0_3_11` remains the passed baseline until explicit V0315 PASS.
