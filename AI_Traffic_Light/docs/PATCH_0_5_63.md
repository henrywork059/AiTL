# V0563 — Centralized frontend polling and cancellation

Candidate `0_5_63`; previous `0_5_62`; accepted baseline `0_5_0`; Update 19 / A04.

## Implementation

The existing useSerialPolling hook delegates single-flight task ownership to a small tested pollingScope core. Committed scope changes, disabling and unmount retire an AbortController; the current in-flight promise remains owned until settlement. Retired errors are suppressed, and migrated callers use isCurrent before publishing. apiClient propagates cancellation without logging it as a transport failure or substituting fallback data, preserving genuine API error codes/request IDs and legacy fallback behavior for other callers. Analytics reads use strict typed requests, filter-keyed results and explicit unavailable display; camera AI preview scopes by camera and active model; dataset label reads cancel on capture changes. No new dependencies, endpoints, backend, UI redesign or signal changes.

## Limitations

Cancellation is client-side and does not guarantee the server stops work. Existing zero-argument polling callers retain their legacy publication behavior until individually migrated; scope retirement suppresses hook-level errors but cannot prevent an unguarded callback from writing. AI preview context polling guards publication but its three underlying reads are not aborted. Genuine errors in analytics now show unavailable rather than fallback zero (intentional behavior correction). Full browser rapid-navigation, React lifecycle and owner Windows/ESP checks remain outstanding. No physical output authorized.

## Validation

Executed the actual pollingScope and apiClient modules with a mocked Node 22 fetch/response test and strict isolated TypeScript compilation, both passed. Git blob hashes for these modules and the test must match the locally tested files. Full checkout unavailable (GitHub DNS failure reproduced); integrated React typecheck/build and full CI pending. Previous 0_5_62 full CI passed ([run 45579569473](https://github.com/henrywork059/AiTL/actions/runs/45579569473)). The new npm test is wired into CI after npm ci. No owner PASS.

```powershell
python scripts/test_frontend_polling_structure.py
Push-Location apps/pc-studio/frontend
npm run test:data-access
npm run typecheck
npm run build
Pop-Location
```

Correction 19a (same candidate): [initial CI run 45580743596](https://github.com/henrywork059/AiTL/actions/runs/45580743596) passed compile/structure and reached the historical V059 regression, which incorrectly expected the pre-cancellation `fetchCameraInference(sourceId)` call. Updated the regression to verify signal forwarding, scope retirement, camera/model restart key and the guard before state publication; retained existing settings, model registry and region checks. No runtime source changed. Reproduced the obsolete predicate and checked all 11 current grouped frontend predicates directly against the actual parent source (12 checks including reproduction); these are source checks, not execution of the full Python test. Direct Git checkout remains blocked by DNS resolution. Corrective full CI, frontend runtime test, TypeScript/build and owner PASS pending. Do not advance until corrective CI passes.

Next Update 20 / S01: evaluate replacement simulation engines, subject to CI.
