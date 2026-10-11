# Start Here — V0317

V0317 / `0_3_17` is the AI workflow and integrity-hardening candidate. Previous candidate: `0_3_16` (unaccepted). Owner-confirmed passed baseline: `0_3_11`.

## What changed

- `AGENTS.md` and the patch playbook now prioritize one-pass authority checks, narrow owner/test/contract reads, minimal edits, targeted validation, and direct atomic GitHub commits.
- Detailed agent guide, checklist and development workflow use the same fast path and explicit escalation rules.
- Documentation-only work can finish without inspecting or changing unrelated application/firmware code; safety and release acceptance rules remain unchanged.

## Update and validate

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The unaccepted candidate also contains focused code-integrity hardening for dataset/training coordination, atomic manual labels, and frontend refresh/error handling. No new features or security changes; the Windows runner and ESP firmware are unchanged. An explicit owner PASS is still required to advance the passed baseline.
