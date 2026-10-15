# Patch 0_4_13 — Quiet slate sidebar

**Candidate:** `0_4_13` · **Previous candidate:** `0_4_12` · **Owner-accepted baseline:** `0_4_0`

## Scope

Sidebar styling and shared nav-color roles only:

- Replace filled, mint-bordered navigation section boxes with muted uppercase headings and 1px dividers.
- Remove the mint left selection strip, selected mint text/fill and trailing dot on page navigation. Use a solid slate selected row with brighter label instead.
- Keep hover subtle, rounded corners small, a distinct boxed brand/title, accessible `aria-current="page"`, keyboard focus indication and all interactive page navigation.
- Preserve light-mode contrast and existing mint functional-control indicators (camera selections, toggles and active tabs).

Existing React routes, cameras, Junction Network cards, APIs and all backend code are unchanged.

## Validation

Added focused static navigation regression and updated older visual tests to the new sidebar intent. Actual frontend TypeScript/build, app launch, Windows visual checks and smoke remain owner acceptance criteria.

Run:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
