# V0574 — Independent network, region, AI review and reproducible experiment candidate

Candidate `0_5_74`; previous `0_5_73`; accepted baseline `0_5_0`. Updates 31 / U02 and 36 / E02 delivered as software candidate milestones. Updates 30, 33, 37 and 38 partial; Update 28 / S04 remains gated. Owner PASS pending.

## Implementation

Crosswalk editor confirms frame availability, withdraws stale preview, locks mutations during save, preserves failed drafts and maps real pointer input through inverse SVG coordinates with side/pointer ownership. Camera-side assignment and independent region polygons persist. Network protects drafts during failed polls, withdraws stale observations, and qualifies camera reassignment/cancel plus topology link creation/edit/delete/recreation. Dataset Review gates save on matching decoded image and label revision, rejects corrupt/wrong-size images and mismatched save/delete identities, supports actual positive/negative annotation edits, cancellation/deletion, managed build and stale rebuild eligibility. Real-clock CDP trials exercise pointer gestures and capture identity. No backend route, data schema, dependency, signal authority or simulator-default changes.

## P4 qualification

Application and test qualification: exact [standard CI 46018941752](https://github.com/henrywork059/AiTL/actions/runs/46018941752) on `9e006c900814f65e3e82c76db98fefb815144560` passed compilation, structure, full offline suite, seeded batch, frontend data-access tests, typecheck, build and blocking audit (zero vulnerabilities reported). [Browser CI 46016827486](https://github.com/henrywork059/AiTL/actions/runs/46016827486) on `f18cd41995fd30ef8be305d1d038bca37cc95942` passed all workspace and renderer tests. Later application-qualification commits changed only the two legacy static regression scripts, preserving side-selection and region invariants while checking the new handler. Browser artifact [15205454907](https://github.com/henrywork059/AiTL/actions/runs/46016827486/artifacts/15205454907) SHA-256 `1f672c0f1a6df01ff17b923d3328f60fee6d0960a0ceb9f6b8199071b4f17328` matched; actual region, junction and review screenshots inspected. Tests use synthetic API fixtures, not ESP hardware or trained-model inference. Exact release-bundle standard CI remains pending at publication.

## P5 reproducible evidence

Isolated 120 s queue-model comparisons: 4 seeds (42, 43, 73, 101), 3 demand levels, 12 matched cases, 36 primary policy rows, 96 intersection fairness rows, 4 busy repeats. [Exact standard artifact 15207277149](https://github.com/henrywork059/AiTL/actions/runs/46018941752/artifacts/15207277149) SHA-256 `421b2abbc180b1ded17904f72e61727b00624b1842cb5b36086c4c19292e0c93` independently matched, all 43 member hashes, 216 primary values and 1056 intersection values reconciled; repeated network/local metrics and scenario identity verified. Cooperative minus adaptive pedestrian wait increases in 4/4 light, 3/4 normal and 4/4 busy cases; busy mean +32.125 person-s, vehicle wait mean -305.875 vehicle-s. Secondary pedestrian-aware policy retains adverse cases and vehicle-wait tradeoffs. No tuning, statistical generalization or field claim. Add a standalone read-only evidence verifier (stdlib, no simulator imports) whose exact staged Git blob was matched to locally tested source. It passed two retained full CI archives, and rejected wrong external digest, altered CSV with original or recomputed member hash, and rehashed altered busy repeat. Integrate full batch verification into standard CI and focused smoke/tamper regression; these new CI integrations await exact release CI. Timeline/decision exports are hash-checked, not semantically replayed by this verifier.

Replay evidence verification (read-only, from AI_Traffic_Light):

```powershell
python scripts/verify_seeded_network_evidence.py <archive.zip> --sha256 <trusted-archive-digest>
```

## P3 and remaining acceptance

Native qualification remains separate: [native CI 46012562415](https://github.com/henrywork059/AiTL/actions/runs/46012562415) and 46011851179 passed; 11 synthetic capture archives/44 images, palette control only, no trusted model holdout. Independently reconciled native/reference normalized timeline metrics and matched resource workloads remain documented in [SIMULATOR_MIGRATION_GATES.md](SIMULATOR_MIGRATION_GATES.md). Finite passage counts match 8 vehicles/14 pedestrians, but native/reference normalized waiting differs (129.4/144.0 vehicle-agent-s; 15.4/57.2 pedestrian-agent-s). Production coordinate calibration/common estimand, trusted detector validation, owner resource budget/Windows and rollback acceptance remain open. Legacy simulator remains default; no public-road signal actuation, no baseline promotion. Partial 30 owner live device/mode acceptance; partial 33 capture/training workflow; partial 37 trusted holdout; partial 38 endurance/master evidence. Updates 32/34 retain dependency gates.

## Owner testing

```powershell
# From repository root
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify footer 0_5_74 Candidate. Back up saved data before testing. Use disposable capture fixtures for destructive tests. Verify camera source selection and no stale preview, side A/B independent region drag/save/reload and failure retry, crosswalk links and camera reassignment/cancel, stale/unavailable status and draft retention, review identity/decode rejection, positive/negative label save, build and delete invalidation. Confirm legacy simulator remains default and existing optional renderer fallback/rollback. Run authorized bench checks only; no public-road outputs. Owner alone confirms PASS.
