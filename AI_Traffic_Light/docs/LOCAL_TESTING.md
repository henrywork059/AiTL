# Local Testing — V0317

Expected release state:

```text
version: 0_3_17
previous_version: 0_3_16
passed_baseline: 0_3_11
status: AI workflow and integrity hardening candidate
```

## Guideline checks

1. Confirm `AGENTS.md`, `PATCH_PLAYBOOK.md`, `AI_AGENT_GUIDE.md`, `AI_AGENT_CHECKLIST.md` and `DEVELOPMENT_WORKFLOW.md` retain the release-state, architecture, safety, runtime-data and testing rules.
2. Verify the new fast path explicitly requires HEAD/version confirmation, owner-first narrow reads, minimal file edits, relevant tests, remote-HEAD recheck and direct non-force push.
3. Confirm `VERSION`, frontend `projectVersion.ts`, changelog, patch document, `START_HERE.md`, this guide and `TEST_READY_CHECKLIST.md` consistently name `0_3_17`; previous `0_3_16`; baseline `0_3_11`.
4. Run `python scripts/check_structure.py` from `AI_Traffic_Light` to validate release/structure consistency on a complete checkout.

## Full owner validation

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

The default command still performs its full preflight, tests, frontend typecheck/build, Git cleanliness and live smoke before starting PC Studio. `-ChangedTests` is optional for routine fast startup, not full acceptance.

No ESP reflash, new feature or API change is expected. Existing UI refresh/error handling has been corrected. Owner PASS is required; `0_3_11` remains the accepted baseline.

## Same-candidate integrity validation

- Run `python scripts/test_dataset_labeling_service.py` to check label persistence, safe YOLO builds and the refusal to replace a dataset during active training.
- Run `python scripts/test_training_service.py` to confirm existing training/early-stopping semantics.
- Run `python scripts/test_frontend_polling_structure.py`, `npm run typecheck` and `npm run build`.
- On Dataset Review, test with an unavailable backend: initial load and Refresh list should show an error.
- Refresh the app while switching simulation on/off: late camera-status responses must not revert the selected mode.
- Try rebuilding the managed dataset during a training job: the request must fail without replacing its files.
