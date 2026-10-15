# Patch 0_4_15 — Dark canvas slightly darker

**Candidate:** `0_4_15` · **Previous:** `0_4_14` · **Owner-accepted stable baseline:** `0_4_14`

## Scope

Change one shared dark-theme canvas token from `#4D4E61` to `#444557`. All other dark surfaces (including the quiet slate sidebar), mint action color, text colors, light appearance and UI functionality remain unchanged.

Update the two prior palette tests that explicitly used the former literal canvas color; their contrast and invalid-token safeguards remain in place. No backend, API, dependencies or hardware changes.

## Validation

Source-level token and test assertions may be checked remotely; the complete Windows runner, typecheck, build, live smoke and user visual approval remain required. V0415 is a candidate, not an accepted release.

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
