# 0_6_0 — Owner-accepted stable release

Stable release `0_6_0`; previous `0_5_78`; accepted baseline `0_6_0`.

On 28 November 2026 the owner explicitly accepted candidate `0_5_78` as PASS and authorized promotion to stable `0_6_0` after CI and merge qualification. Exact candidate HEAD `ff76e1a465b031990e5184626f4a08f762cfd0ff` passed [release CI 46042804089](https://github.com/henrywork059/AiTL/actions/runs/46042804089) and [PR CI 46042810610](https://github.com/henrywork059/AiTL/actions/runs/46042810610). [PR #8](https://github.com/henrywork059/AiTL/pull/8) merged as `9b93a9e653e9e4b5d3b0d96b5c2bb5a3db288a59`; comparison confirmed no file differences between the candidate and the merge tree. Earlier implementation [native CI 46041638617](https://github.com/henrywork059/AiTL/actions/runs/46041638617) and standard CI 46041638586 passed. See [PATCH_0_5_78](PATCH_0_5_78.md) for the coordinate qualification and limitations.

This is an owner-authorized release metadata promotion only: no application logic, firmware, saved configuration, simulation default or physical output authority changes. Owner PASS is explicit acceptance, not an independently witnessed Windows or hardware test. Stable means the accepted student-prototype baseline, not certified public-road readiness. S04 migration remains incomplete: physical camera calibration, production coordinate/wait equivalence, trusted detector validation and resource qualification remain separate outstanding gates. Original roadmap remains 30/39 delivered; no additional development objective started. Promotion CI on the exact stable commit must be checked separately; do not infer a new CI result from the preceding candidate.

## Run the accepted baseline

From the repository root:

```powershell
git switch main
git pull --ff-only origin main
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Expected release label: `0_6_0 Stable`. Verify legacy simulator default and existing saved regions. This command is an owner-side check, not a claimed execution in this promotion. Development branch remains `feature/interactive-3d-simulation`.
