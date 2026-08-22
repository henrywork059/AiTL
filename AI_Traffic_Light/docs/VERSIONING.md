# Versioning and Acceptance State

AiTL uses underscore release versions such as `0_2_5`. This document defines the rules; it intentionally does not own the current version snapshot.

## 1. Canonical source

Root `VERSION` is authoritative and contains:

```text
version
status
previous_version
passed_baseline
notes
```

Backend runtime version surfaces read it through `app/core/project_version.py`. Frontend fallback/navigation uses the checked mirror in `src/constants/projectVersion.ts` where required by the current implementation.

To learn the current candidate, read `VERSION`; do not copy a version number from this guide.

## 2. Meaning of fields

- **version** — candidate currently under development/testing.
- **status** — concise description/state of that candidate.
- **previous_version** — version immediately preceding the candidate according to the repository's chosen release sequence.
- **passed_baseline** — latest version explicitly confirmed working by the owner.
- **notes** — important release-state context and limitations.

`version` and `passed_baseline` may differ. That is normal while a candidate is being tested.

## 3. Acceptance rule

Only explicit owner acceptance promotes `passed_baseline`.

These do **not** count as acceptance:

- automated tests;
- successful build;
- GitHub upload/merge to `main`;
- an AI-agent judgment;
- "test-ready" documentation;
- a patch ZIP being produced.

## 4. Same-candidate repair rule

If a candidate has a bug or needs hardening before owner acceptance, normally repair that same candidate. Do not silently increment the version.

The owner may explicitly request a new version even if the current candidate is unaccepted. Record such exceptions clearly so `passed_baseline` remains truthful.

## 5. Normal increment rule

After explicit acceptance, normal development proceeds from the accepted candidate to the next agreed version. Small increments usually advance the final component; larger milestone increments are allowed when deliberately chosen.

Version numbers describe project releases, not semantic compatibility guarantees.

## 6. Version change checklist

For an actual version change:

1. update root `VERSION`;
2. update any required checked frontend version mirror;
3. keep backend runtime metadata derived from root `VERSION`;
4. add/update the relevant `CHANGELOG` and `PATCH_<version>` section;
5. update `START_HERE`, `LOCAL_TESTING`, and `TEST_READY_CHECKLIST`;
6. update README/function/roadmap docs when capability status changes;
7. run structure/version-surface checks.

Do not modify historical patch/changelog facts just because they contain old versions.

## 7. Documentation anti-drift rule

Long-lived guides (`HUMAN_GUIDE`, `DEVELOPMENT_WORKFLOW`, `AI_AGENT_GUIDE`, this file) should not contain a hard-coded current candidate snapshot. Current release state belongs in:

```text
VERSION
START_HERE.md
PATCH_<version>.md
LOCAL_TESTING.md
TEST_READY_CHECKLIST.md
CHANGELOG.md
```

See `DOCUMENTATION_MAP.md`.

## 8. Package/tool versions

Npm/Python package versions are not automatically the AiTL release version. Package manifests may use their ecosystem's dotted versions and should only be synchronized when the patch explicitly requires it.

## 9. Patch ZIP naming

Use a descriptive candidate name, for example:

```text
AiTL_V025_<short_description>_patch.zip
```

The archive remains changed-files-only and each member starts with `AI_Traffic_Light/`.
