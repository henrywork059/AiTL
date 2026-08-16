# Versioning and Acceptance State

AiTL uses underscore project versions such as `0_2_3` and `0_2_4`.

## Canonical source

Root `VERSION` is authoritative and contains `version`, `status`, `previous_version`, `passed_baseline`, and `notes`. Backend runtime version surfaces read it through `app/core/project_version.py`; frontend fallback/navigation uses the checked mirror in `src/constants/projectVersion.ts`.

## Current state

```text
candidate:         0_2_4 (V024)
previous_version:  0_2_3 (V023)
passed_baseline:   0_2_2 (V022)
```

The owner explicitly accepted V022 before requesting V023. The owner later explicitly requested V024 without explicitly accepting V023, so the passed baseline remains V022. V024 remains unaccepted until the owner completes its manual acceptance checks and explicitly confirms it passed.

## Candidate versus passed baseline

- **version** — patch currently under development/testing.
- **passed_baseline** — latest version explicitly confirmed working by the owner.

Automated tests, builds, GitHub upload, or agent judgment never promote `passed_baseline`.

## Increment rule

If a candidate has a bug before acceptance, normally repair that same candidate; do not silently create the next version. The owner may explicitly override this rule, as happened when V024 was requested before V023 acceptance. After explicit acceptance, normal development continues from the accepted version unless the owner requests another version.

## Version surfaces

For a real version change:

1. update root `VERSION`;
2. update `src/constants/projectVersion.ts`;
3. keep backend version surfaces derived from `project_version.py`;
4. update changelog/patch/testing/current-state docs;
5. run `scripts/check_structure.py`.

Historical changelog/patch documents intentionally retain old release values.

## Package-manager versions

Tool manifests such as npm `package.json` use dotted semantic versions and are not the authoritative AiTL release state unless a patch explicitly synchronizes them.

## Patch ZIP naming

Use a descriptive candidate name such as `AiTL_V024_maintenance_hardening_patch.zip`. Archives remain changed-files-only and every member path starts with `AI_Traffic_Light/`.
