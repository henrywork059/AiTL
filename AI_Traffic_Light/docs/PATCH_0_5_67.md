# V0567 — Optional SUMO shadow integration

Candidate `0_5_67`; previous `0_5_66`; accepted baseline `0_5_0`; Update 22 / S02. Owner PASS pending.

## Implementation

The existing CameraFrameService remains authoritative. Optional `MESH_SUMO_SHADOW=1` forwards committed virtual phases to a bounded asynchronous worker and a dedicated libsumo child process through local IPC (no TraCI network listener). Four 50 ms legacy steps produce one 200 ms shadow step; mixed, yellow, flashing or unknown phases grant all-red. Restricted east–west straight vehicle movements and pedestrian crossings are checked against the generated link/conflict matrix, native link mapping and permission readback. Opposing entry is withheld when internal vehicle/crossing edge occupancy is detected. Reset, stop, engine error or backlog overflow invalidate snapshots. Pause stops new legacy ticks, but queued steps may drain. The default is disabled; no automatic dependency install or changes to existing camera/detection/decision/physical outputs. `GET /api/camera/simulation/shadow` is read-only and returns separately labelled synthetic diagnostics; snapshots can lag the authoritative clock.

## Verified evidence

Executed release-gate evidence for application revision `fc3508e52adf460a19fe32b74c8324903d90e35f`: [standard CI 45737386040](https://github.com/henrywork059/AiTL/actions/runs/45737386040) passed compilation, structure, offline regressions (including camera integration and runtime), frontend regressions/typecheck/build and blocking npm audit (0 reported vulnerabilities). [Native CI 45737386082](https://github.com/henrywork059/AiTL/actions/runs/45737386082), Windows x64 Python 3.10.11, passed exact hash-pinned installation, pip check, version-specific PyPI advisory checks (zero active advisories for all five packages), adapter/child process/runtime tests, native reference and controlled simulation. The earlier [Python 3.11 native CI 45736465611](https://github.com/henrywork059/AiTL/actions/runs/45736465611) also passed the reference trial. Both native-plan reference runs reproduced the TraCI digest `34c24376cf005cdb3d5f9ab0b4aab822847970f49b380fdf139fb0426ee76097` exactly. Each controlled run (seed 42, 300 s, 0.2 s step, 1500 ticks) observed 24 agents, completed 12/12 vehicles and 12/12 pedestrians, and produced digest `28a85055d3ef862650da3fce4aef5e8018f4eb37a9e0f2d3bb017eecf4e7c902`. Observed states were `rrrrrGrrrrrrrGrrrrrr`, `rrrrrrrrrrrrrrrrGGGG`, and `rrrrrrrrrrrrrrrrrrrr`; no simultaneous vehicle/pedestrian grants in the tested fixture. Asynchronous runtime and native failure recovery passed. [Retained artifact 15080205533](https://github.com/henrywork059/AiTL/actions/runs/45737386082/artifacts/15080205533), expires 10 December 2026 09:42 HKT. Results verified from CI logs; newest raw artifact not independently re-inspected in this release step.

## Owner acceptance

```powershell
# From repository root; normal owner acceptance uses legacy default.
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
Remove-Item Env:MESH_SUMO_SHADOW -ErrorAction SilentlyContinue
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Optional shadow verification is a separate controlled exercise, not required for default acceptance. Use an existing trusted Windows x64 Python 3.10/3.11 backend virtual environment after the default runner has initialized it. Stop the running PC Studio backend first. From `AI_Traffic_Light/apps/pc-studio/backend`:

```powershell
& .\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --only-binary=:all: --no-deps --require-hashes -r requirements-sumo-shadow-win-x64.txt
if ($LASTEXITCODE -ne 0) { throw 'Optional SUMO installation failed' }
& .\.venv\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
$env:MESH_SUMO_SHADOW = '1'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In the existing frontend, enable simulation, observe the diagnostics at `http://127.0.0.1:8000/api/camera/simulation/shadow`, pause/resume, change density and switch off simulation. Verify the legacy scene is unchanged, the shadow advances separately and resets/clears on stop. Stop the optional backend with Ctrl+C; remove `Env:MESH_SUMO_SHADOW` and restart the normal runner to roll back. Do not enable with live-road hardware or expose the optional service to untrusted networks.

## Limits and next step

Evidence class: actually executed synthetic simulation, not field data. Restricted demand, geometry, and illustrative permission cycle differ from the legacy simulator; no matched performance/controller benefit, physical clearance certification, endurance, or owner browser/ESP PASS is established. The native controlled trial and camera integration regression are separate checks, not an end-to-end native PC Studio session. PyPI advisory metadata is time-specific and does not audit bundled native DLLs. Optional packages are pinned to 1.28.0 with wheel hashes; native dependencies are optional and not automatically installed. Keep the existing engine authoritative and opt-in mode restricted to trusted local synthetic evaluation. No public-road actuation, partnership or pilot. Candidate delivery 22/39; next Update 23 / S03 (replacement 3D road renderer).

## Update 23a — Three.js renderer trial

23a / S03 preparation (same candidate): [0_5_67 release CI 45738218138](https://github.com/henrywork059/AiTL/actions/runs/45738218138) passed. Select exact Three.js and @types/three 0.187.0 (MIT, upstream https://github.com/mrdoob/three.js and https://www.npmjs.com/package/three ; type definitions https://www.npmjs.com/package/@types/three). Runtime module and type package dependency closure must be reviewed after npm resolves the lock. No CDN, loaders, assets or new production packages. Local Node 22.16.0 pure geometry regression passed (reference-pixel road bounds, nine zebra stripes, two stop lines, lane gaps, four mirrored views, camera pose); npm view failed EAI_AGAIN, so do not invent lock/integrity or claim WebGL/typecheck/build passed. Add canonical road surface model aligned with camera_frames.py (1280x720 synthetic coordinates; existing one straight road/crosswalk, not SUMO junction). Isolated Three.js trial module draws road, raised pavements, kerbs, lane markings, crossing, stop lines, signal posts, coarse snapshot proxies; accepts camera orbit/pitch/zoom and disposes resources, context-loss callback. Standalone trial not imported by the production component; existing CSS renderer, editor and all source/camera/control contracts unchanged. Read-only feature-branch Windows trial generates and retains npm manifests, audits locked dependency closure, typechecks/builds standalone renderer, runs actual headless Edge WebGL software-rendered draw/top-view/context-loss/disposal smoke and captures screenshot, and verifies existing frontend build. Browser automation may be blocked by runner GPU/Edge support; inspect exact trial logs and screenshot before adoption. No performance benchmark or UI acceptance. Update 23 remains in progress, 22/39 delivered; owner PASS pending.

## Update 23b — TypeScript trial correction

23b / S03 corrective trial (same candidate): [23a renderer trial 45738796215](https://github.com/henrywork059/AiTL/actions/runs/45738796215), job 139638416734, passed exact resolution, npm ci, blocking audit (zero reported vulnerabilities), pure geometry test and production-source typecheck, then failed TS5112 because TypeScript 7.0.2 rejects explicit source files alongside the existing tsconfig.json. Standalone build, browser smoke and screenshot skipped. Independently downloaded artifact 15080216627: manifest Git blob b72a6215cf357fb94a83f23a8f4af82c6366a75d, lock blob faabff6777280a9ab2f52ff47d2e5f9a3bf5d34b; 76 -> 84 lock entries, all non-root packages HTTPS npm registry with SHA-512 integrity. Reviewed npm-generated diff: all existing package entries unchanged; three 0.187.0 MIT is sole new runtime dependency, @types/three 0.187.0 MIT and its six dev-only dependencies @dimforge/rapier3d-compat 0.12.0 Apache-2.0, @tweenjs/tween.js 23.1.3 MIT, @types/stats.js 0.17.4 MIT, @types/webxr 0.5.24 MIT, fflate 0.8.3 MIT, meshoptimizer 1.1.1 MIT. No new package adoption until browser evidence; no imports from these dev-only runtime helpers. Replace the brittle CLI invocation with a dedicated trial tsconfig extending the production settings and tsc --project; additionally verify immediate WebGL readPixels color variation and error status for perspective/top views, not only draw calls. Re-executed pure geometry regression on local Node 22.16.0; passed. Local installed TypeScript 5.8.3 is not the locked 7.0.2 and Three.js is unavailable locally; no new native typecheck or actual browser execution claimed. Existing production dependencies/renderer, region editor, camera and signal authority unchanged. Corrective CI pending; no screenshot available yet, 22/39 delivered.
