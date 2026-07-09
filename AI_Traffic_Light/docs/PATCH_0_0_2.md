# Patch 0_0_2 — Human and AI-Agent Instructions

## Purpose

This patch adds explicit working instructions for both:

```text
human users / project maintainers
AI agents / coding assistants
```

The goal is to make future development safer, more consistent, and easier to patch through GitHub web upload.

## Files changed or added

```text
README.md
VERSION
CHANGELOG.md
AGENTS.md
docs/AI_AGENT_GUIDE.md
docs/HUMAN_GUIDE.md
docs/PATCH_0_0_2.md
```

## Main additions

- Root-level `AGENTS.md` for AI agents.
- Detailed `docs/AI_AGENT_GUIDE.md` for automated coding/documentation assistants.
- Human-facing `docs/HUMAN_GUIDE.md` for project usage, upload workflow, safety, and development order.
- Version references updated to **0_0_2**.

## Functional impact

No app behavior is changed in this patch.

This is a documentation-only patch.

## Upload note

This patch follows the new patch rule:

```text
Only changed files are included.
```

Upload the contents into the existing `AI_Traffic_Light/` folder on GitHub and replace matching files.
