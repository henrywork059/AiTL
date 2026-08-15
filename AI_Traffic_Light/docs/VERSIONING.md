# Versioning and Acceptance State

AiTL uses underscore project versions such as `0_1_7` and `0_2_0`.

## Canonical source

Root `VERSION` is the authoritative current-state record and must contain:

```text
version: ...
status: ...
previous_version: ...
passed_baseline: ...
notes: ...
```

Backend runtime version surfaces read this file through `apps/pc-studio/backend/app/core/project_version.py`. Frontend fallback/navigation surfaces import `apps/pc-studio/frontend/src/constants/projectVersion.ts`, a build-safe mirror that `scripts/check_structure.py` verifies against root `VERSION`.

## Candidate versus passed baseline

These are different concepts:

- **version** — the patch currently under development/testing;
- **passed_baseline** — the latest version the owner explicitly confirmed working.

If those values differ, the current version is not automatically accepted.

Current state:

```text
candidate:       0_2_0 (V020)
previous_version: 0_1_7
passed_baseline:  0_1_7 (V017)
```

V020 intentionally skipped `0_1_8` and `0_1_9` by owner instruction.

## Increment rule

When the current candidate is still unaccepted, bug fixes/hardening normally stay on that candidate.

After the owner explicitly accepts `0_2_0`, normal small increments continue from it, for example:

```text
0_2_0 → 0_2_1 → 0_2_2
```

A larger milestone may advance another component, but do not skip versions unless the owner explicitly requests it.

## Acceptance rule

Never change `passed_baseline` because:

- unit tests pass;
- frontend builds;
- the patch is uploaded to GitHub;
- an AI agent believes the UI should work.

Only explicit owner acceptance promotes the baseline.

## Runtime/version-surface rule

For a real version change:

1. update root `VERSION`;
2. update the shared frontend `src/constants/projectVersion.ts` mirror;
3. keep frontend pages/API fixtures importing that shared constant and backend version surfaces derived from `project_version.py`;
4. update changelog/patch/testing docs;
5. run `scripts/check_structure.py` to detect version-surface drift.

Historical docs/changelog entries intentionally contain old versions and should not be treated as stale runtime labels.

## Tool-specific package versions

The project release uses underscore notation. Tool manifests such as npm `package.json` require dotted semantic versions. Those package-manager fields are not the authoritative AiTL project release label unless the patch explicitly synchronizes them.

If package metadata is intentionally changed, update its lockfile metadata in the same change; do not edit only one side.

## Patch ZIP naming

Use a descriptive name that identifies the candidate and purpose, for example:

```text
AiTL_V020_maintenance_hardening_patch.zip
AiTL_V021_<feature>_patch.zip
```

The archive itself remains changed-files-only and preserves paths beginning with `AI_Traffic_Light/`.
