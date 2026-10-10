# Patch 0_3_16 — Focused startup checks

V0316 / `0_3_16` is the next explicitly requested candidate after V0315 / `0_3_15`.
The owner-confirmed passed baseline is still `0_3_11`.

## Implemented

- Optional `-ChangedTests` selects offline regression tests by changed Git file/family, instead of launching the full suite.
- Git changes are captured during pull and passed through the runner's guarded one-time reload. Without new pulled changes, the latest commit is used.
- Changed frontend code still runs typecheck/build. Shared/unknown or dependency changes conservatively trigger the full suite.
- Structure/version validation, runner regression, dependency update policy, safe process handling, live readiness and smoke checks remain in place.
- Default startup still performs the full set of checks; `-SkipTests` retains its existing behavior.

## Limitations

Focused mode is a speed-oriented test selection, not proof of full regression coverage. Selection is at file/feature family level, not at code-line level. Hardware-only diagnostics remain manual.
Application APIs, simulation, persistence, traffic safety logic, model formats, and firmware are unchanged.

## Owner validation

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests
```

Run the default command without `-ChangedTests` before accepting this candidate. Only an explicit owner PASS updates `passed_baseline`.
