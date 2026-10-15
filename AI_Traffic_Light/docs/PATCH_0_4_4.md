# Patch 0_4_4 — Dark theme structure-validator repair

Candidate: `0_4_4`. Previous candidate: `0_4_3`. Accepted stable baseline: `0_4_0`.

The Windows V0403 update/test/run log showed a hard stop in `scripts/check_structure.py`. A legacy guard required a literal `#121212` dark base while the V0403 theme intentionally uses `#0E1725`. The guard now validates that a hex-format dark base token is defined inside the dark-theme media query and referenced by the dark canvas.

The V0403 visual regression covers acceptance of the new base and rejection of an invalid base token. No application logic or CSS colors change. Windows/frontend runtime and UI acceptance are pending.

Run from your repository root:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
