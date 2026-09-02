# Patch 0_3_13 — Code management and optimization

V0313 / `0_3_13` is a code-quality and optimization candidate created at the owner's explicit request after unaccepted V0312. `0_3_11` remains the owner-confirmed passed baseline until explicit V0313 acceptance.

## Purpose

Reduce maintenance cost and repeated work in frequently refreshed Junction Network and validation paths without changing user-facing contracts or prototype behavior.

## Frontend management

Junction Network responsibilities are now clearer:

- `JunctionNetworkPage.tsx` keeps page state, mutations, selection, drag interaction and save/reset orchestration;
- `components/junctions/JunctionNodeCard.tsx` owns node-card presentation only;
- `lib/junctionNetworkView.ts` owns small pure display/config helpers;
- repeated link/source lookups use memoized ID/source maps instead of repeated linear scans during render.

The V0312 wider/non-clipping card layout remains unchanged.

## Backend optimization

`JunctionNetworkOverviewService` now normalizes each saved ESP camera into its UI projection once per overview poll and reuses that projection for junction assignment and summary work. A focused regression counts these conversions and requires exactly one projection per saved camera for each overview.

The existing observability boundary is unchanged: only the junction resolved from the shared selected physical/simulation source receives current AI/simulation traffic metrics.

## Validation simplification

`scripts/check_structure.py` is now the single structural/release-consistency authority. It owns current version/document synchronization, durable workflow guards, architecture checks, version-source checks, atomic persistence and serial-polling invariants.

The duplicate `test_release_documentation_consistency.py` regression was removed. `update_test_run.ps1` now runs one `Project structure and release consistency` preflight plus its runner self-regression before dependency work.

The normal Windows command, dependency-change optimization, recursive reload guard, automatic regression discovery, process ownership safety, live smoke and runtime-data preservation remain unchanged.

## Compatibility

V0313 does not change:

- HTTP endpoints, API envelopes, request IDs or stable error behavior;
- `config/intersections.json` schema or camera assignment semantics;
- Junction Network save/reset/reassign behavior;
- the single-selected-source live AI pipeline boundary;
- dataset, labeling, training, inference or model workflows;
- simulation/adaptive signal behavior;
- V0310 production ESP32-CAM `ATL1` / `aitl-tcp-jpeg-v1` transport;
- physical/public-road safety boundary.

## Acceptance target

Run:

```powershell
& "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\scripts\update_test_run.ps1"
```

Expected preflight now includes:

```text
Python compile
Project structure and release consistency
Update/test/run runner regression
```

There should be no separate `Release documentation consistency` step.

After automated checks, verify **Traffic → Junction Network** with multiple junctions/cameras: drag nodes, save/reload layout, assign/reassign cameras, select primary/None, edit links, confirm full card content remains visible, and confirm only the selected source's resolved junction shows live traffic observations.

`0_3_11` remains the passed baseline until the owner explicitly confirms V0313 passes.
