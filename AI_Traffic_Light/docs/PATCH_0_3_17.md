# Patch 0_3_17 — AI workflow and guidelines efficiency

`0_3_17` is the owner-requested candidate after unaccepted `0_3_16`. Passed baseline remains `0_3_11`.

## Goal

Reduce AI time spent reading and re-reading unaffected code, generating broad edits, running irrelevant tests and creating incremental commits—without lowering accuracy or safety.

## Implemented

- **First-pass routing:** confirm current GitHub HEAD and root `VERSION`, read mandatory instructions and short playbook once; locate the owning file by path/symbol before fetching details.
- **Progressive reading:** initially inspect the responsible module/document, closest focused regression and directly affected contract, using narrow ranges. Expand only for demonstrated dependencies or uncertainty.
- **Stop condition:** begin editing when ownership, intended behavior, contract and regression are established; do not audit the whole repository for a narrow request.
- **Minimal editing:** reuse the existing owner, avoid speculative files/dependencies/refactoring and examine the exact change manifest/diff.
- **Tiered validation:** run focused checks first, widen for safety/shared-contract risk or ambiguous coverage; keep the full owner runner as acceptance validation.
- **Fast publishing:** use direct GitHub writes, prefer one atomic multi-file commit, verify remote HEAD, never force push and verify the final commit/version.
- **Docs-only lane:** inspect/edit only responsible guides and release surfaces; avoid unrelated runtime/test/hardware changes.

Updated the mandatory agent rules, playbook, detailed guide, checklist and development workflow. Release/testing docs and frontend version mirror are synchronized.

## Unchanged

FastAPI/backend and React/frontend source behavior; scripts/startup/test selection; ESP firmware and transport; camera inference and junction topology; simulated traffic signal safeguards; HTTP/data contracts and persisted/runtime data; owner-only PASS/baseline promotion.

## Validation / acceptance

Validate release metadata and structure with `python scripts/check_structure.py` on a complete checkout. Owner uses the normal Windows `scripts/update_test_run.ps1` for full candidate acceptance; no hardware reflash is needed. A guidance-only patch does not prove faster runtime or AI execution until observed in subsequent development tasks.

`0_3_11` remains the accepted baseline until explicit owner PASS.

## Same-candidate integrity hardening

Following a repository integrity review, this unaccepted candidate received focused fixes without a version increment:

- Manual dataset labels now reuse the existing shared atomic JSON writer, removing the redundant custom writer.
- Managed YOLO dataset rebuilds are coordinated with training startup and rejected with the existing dataset-not-ready error while a training run is active. Training files are not swapped underneath a running worker.
- The application bulk refresh now shares one in-flight request, and older bulk camera-status responses cannot overwrite a completed simulation-mode transition.
- Dataset Review initial loading and manual Refresh list report failed requests through the existing UI error state instead of leaving unhandled promise rejections.
- Existing dataset and frontend regressions were extended. No new feature, security change, firmware edit or dependency was added.
