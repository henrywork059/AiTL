# Local Testing — V0314

Expected release state:

```text
version: 0_3_14
previous_version: 0_3_13
passed_baseline: 0_3_11
status: frontend polling reliability and code optimization candidate
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

## V0314 focused coverage

Important checks include:

- `scripts/check_structure.py` — release consistency plus a frontend-wide prohibition on `window.setInterval`;
- `scripts/test_frontend_polling_structure.py` — shared serial hook behavior and every registered periodic frontend surface;
- inherited camera, traffic, signal, network, dataset, labeling, training, inference, persistence and runner regressions;
- frontend TypeScript typecheck and production build.

## Manual V0314 checks

Exercise these pages for several polling cycles:

- **Operate → Camera Diagnostics** while a diagnostic run is active;
- **Data → Dataset Capture** while camera/simulation status changes;
- **AI → Live AI** with no model, a loaded model, and an unavailable backend/model error if practical;
- **System → Logs**;
- **Traffic → Analytics**, changing mode, time window, region/flow scope and class;
- **AI → Train / Export**, including idle/running status.

Confirm each page updates normally, query/filter changes refresh promptly, no duplicated request bursts appear, and errors remain visible/recoverable.

No ESP firmware reflash is required for V0314.

`0_3_11` remains the passed baseline until the owner explicitly confirms V0314 PASS.
