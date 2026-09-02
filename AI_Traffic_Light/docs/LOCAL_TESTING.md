# Local Testing — V0313

Expected release state:

```text
version: 0_3_13
previous_version: 0_3_12
passed_baseline: 0_3_11
status: code management and optimization candidate
```

## Normal update / test / run

From any PowerShell directory:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Expected sequence:

```text
fast-forward main
→ reload pulled runner exactly once
→ Python compile
→ Project structure and release consistency
→ Update/test/run runner regression
→ dependency refresh only when manifests changed
→ automatic zero-argument offline regressions
→ frontend typecheck/build
→ Git tracked-cleanliness check
→ safely replace only AiTL-owned PC Studio listeners
→ live backend smoke
→ launch frontend/backend
```

There should be no separate `Release documentation consistency` preflight because `check_structure.py` now owns those checks.

Force dependency refresh only when needed:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -RefreshDependencies
```

## V0313 focused coverage

Important checks include:

- `scripts/check_structure.py` — the single structural/release-consistency authority plus durable ownership/persistence/polling guards;
- `scripts/test_update_test_run_script.py` — reload safety, dependency optimization, one structural preflight authority, automatic regressions and safe process replacement;
- `scripts/test_junction_network_overview.py` — one ESP camera projection per saved camera per overview while preserving honest selected-source observation behavior;
- `scripts/test_junction_network_frontend_structure.py` — page/component/helper ownership, memoized lookup maps, navigation/API wiring and non-clipping node layout;
- inherited Junction Network persistence, traffic, camera, dataset/training/inference, simulation and signal regressions.

## Manual V0313 checks

Open **Traffic → Junction Network** and confirm:

- existing saved node positions and links load;
- nodes still drag and save normally;
- multiple cameras can still be assigned to one junction;
- reassigning a camera between junctions still asks for confirmation;
- Primary camera and explicit None still save/reload correctly;
- link add/remove/travel-time editing still works;
- full node title/ACTIVE/load/phase/event/warning content remains visible;
- only the junction resolved from the shared selected source receives current live traffic values;
- other junctions continue to show unavailable live load rather than copied data.

No ESP firmware reflash is required for V0313.

`0_3_11` remains the passed baseline until the owner explicitly confirms V0313 passes.
