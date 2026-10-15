# Patch 0_4_12 — Junction card static-test selector repair

**Current candidate:** `0_4_12`. **Previous candidate:** `0_4_11`. **Accepted stable baseline:** `0_4_0`.

V0411's Windows updater passed project structure, polling, network structure and palette tests, but stopped at `test_v0411_junction_card_layout.py` when checking that `.junction-node-alerts` centers its content.

The CSS has two occurrences of that selector: a grouped rule setting shared flex alignment and a separate rule setting `justify-content: center`. The test helper's unanchored regex chose the first, so it reported an error despite the intended declaration existing.

V0412 anchors selector matches to CSS rule starts and uses the last matching rule (the later explicit alignment override), with a focused example showing that an earlier grouped rule is skipped. This is **test-only behavior**; runtime CSS and JSX remain unchanged.

To validate on Windows:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```

Windows frontend typecheck/build, live smoke and user visual PASS still pending.
