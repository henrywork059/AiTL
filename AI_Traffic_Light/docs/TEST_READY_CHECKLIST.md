# V039 Acceptance Checklist

- [ ] `VERSION` is `0_3_9`; previous is `0_3_8`; passed baseline remains `0_2_4`.
- [ ] `docs/PATCH_0_3_9.md`, `CHANGELOG.md`, and the shared frontend `PROJECT_VERSION` all identify the same V039 candidate.
- [ ] The normal command is reusable from any PowerShell working directory:

  ```powershell
  & "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
  ```

- [ ] The helper requires local `main`, refuses tracked local edits, and updates only with `git pull --ff-only origin main`.
- [ ] The pulled runner reloads itself before continuing so the newest workflow is used.
- [ ] Backend/training dependencies, Python compile, structure check, backend regressions, frontend dependencies/typecheck/build, Git whitespace/cleanliness and live backend smoke all run in the normal full workflow.
- [ ] If an older AiTL PC Studio backend is listening on port 8000, the helper identifies its AiTL ownership and stops the relevant process tree automatically.
- [ ] If an older AiTL frontend is listening on port 5173, the helper identifies its AiTL ownership and stops the relevant process tree automatically.
- [ ] After restart, backend health succeeds on port 8000 and the frontend becomes ready on strict port 5173.
- [ ] A second normal invocation while PC Studio is already running completes without a separate manual port-kill step.
- [ ] An unrelated application using 8000 or 5173 is never terminated automatically and causes a clear safety error instead.
- [ ] Runtime/user data is preserved; no `git clean` or destructive generated-data cleanup is used.
- [ ] `scripts/test_update_test_run_script.py` covers idempotent AiTL restart ownership and unrelated-port protection.
- [ ] V038/R10 Camera Diagnostics remains functionally unchanged, including adaptive production/R5/R8/R9/R10 dispatch and diagnostic state restoration.
- [ ] Existing Camera Sources, Live AI, simulation, Dataset Capture/Review, training, model management, analytics, signal logic and network-simulation regressions remain passing.
- [ ] No stable API envelope, error-code, production camera protocol or signal-control behavior changes in V039.
- [ ] Physical/public-road traffic-control authority remains out of scope.
- [ ] Owner explicitly accepts V039 before `passed_baseline` changes.
