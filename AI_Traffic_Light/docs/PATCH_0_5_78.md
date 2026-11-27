# V0578 — Qualified simulator editor-edge coordinate compatibility (Update 28B)

Candidate `0_5_78`; previous `0_5_77`; accepted baseline `0_5_0`. Update 28B only. The software semantic coordinate and saved-region compatibility objective is qualified; no production camera calibration or full S04 migration acceptance. Original roadmap count remains 30/39 delivered, not owner acceptance.

Exact 0_5_77 release CI 46040786995 passed. Exact implementation HEAD `9950196253efabb69e6b85a28d1e60f90ec62669`: [standard CI 46041638586](https://github.com/henrywork059/AiTL/actions/runs/46041638586) and [native CI 46041638617](https://github.com/henrywork059/AiTL/actions/runs/46041638617) passed. [Fresh native artifact 15221111551](https://github.com/henrywork059/AiTL/actions/runs/46041638617/artifacts/15221111551) independently downloaded and SHA-256 matched `b0a8a8220924ecd01d44e9ecc35d6c905fba21db3ee1fca22ea3e6e6a0d2cdf5`. Independent NumPy interpolation, per-view polygon ray crossings and decoded image comparisons verified 11 capture archives (9 standard midblock, 1 compact, 1 wide), 44 exact decoded mirrored views, 556 truth assignments and class/kind counts, 154 truth-region and 154 palette-region outlines, 11 disposable saved-crosswalk fixture SHA-256 digests and the retained unchanged-after-preview records. All 556 truth anchors were inside the tested semantic domain; first matching assignments crossing 34, slanted 290, full-frame fallback 232. The palette outline check is not a trained detector or an independent palette detection accuracy evaluation. Actual integrated native CI exercised temporary save/reload, side-specific A/B geometry, legacy side filter, inclusive full-frame bounds, original polygon preservation and read-only preview. The independently checked retained fixture bytes support integrity; the temporal unchanged-after-preview assertion is from the executed CI trial. Actual executed synthetic evidence, not field data.

Root cause: legacy editor uses continuous image-edge coordinates with inclusive 0..1280 / 0..720 bounds; older ordered-region preview used raster pixel-centre bounds and mirror arithmetic. Corrected edge mirror uses width-x/height-y; native centre landmarks convert by +0.5 to edge coordinates; declared semantic crossing/road knots remain. Additive mapping contract `semantic_midblock_image_edges_v2` and landmarks disclose transform version while preserving existing assignment identifier and request shape. Slanted edges split at band boundaries; per-view bottom-centre is inverse mapped into the original ordered polygon, strict first match, explicit null outside domain. Native pixel-centre profile and historical rectangle-preview contract unchanged; saved production data, production counting/control, camera inference and firmware unchanged. Calibration limitations: no verified homography, perspective/lens distortion, mounting angle, physical landmark correspondence or real-camera calibration; vertically flipped box bottom centres and strict boundary memberships need not be invariant. No production coordinate parity or trusted trained-detector claim. Legacy simulator remains default, physical actuation prohibited, owner PASS pending. Prior PR #8 CI 46042448011 and exact 0_5_78 release/PR CI are merge gates, not presumed passed.

## Owner validation

From repository root:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify footer `0_5_78 Candidate`, legacy default and unchanged saved regions. Check both camera-side polygons and reload; isolated preview must not modify saved data or grant detector/control authority. Focused test: `python AI_Traffic_Light/scripts/test_native_compatibility.py`. Audit retained ZIP: `python AI_Traffic_Light/scripts/verify_s04_evidence.py <archive-path> --sha256 b0a8a8220924ecd01d44e9ecc35d6c905fba21db3ee1fca22ea3e6e6a0d2cdf5 --tamper-check`. Physical calibration and owner Windows acceptance remain separate.


## Subsequent owner acceptance and promotion (28 November 2026)

The owner explicitly accepted 0_5_78 as PASS. Exact release CI 46042804089 and PR CI 46042810610 passed; PR #8 merged as 9b93a9e653e9e4b5d3b0d96b5c2bb5a3db288a59. Stable promotion to 0_6_0 with accepted baseline 0_6_0 was authorized; see PATCH_0_6_0.md. This supersedes historical pending acceptance wording above without changing the recorded technical limitations.
