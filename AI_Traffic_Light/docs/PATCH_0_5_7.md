# Patch 0_5_7 — Crossing-first Network

Current candidate `0_5_7`; previous candidate `0_5_6`; owner-accepted baseline `0_5_0`.

- Crosswalks appears above Network in Traffic. Every saved crossing automatically appears as a movable crossing box. A separate Network node is not necessary.
- Connections are defined by numbered edges 1–4 and persisted through the existing atomic `/api/crosswalks` PUT with optional `network.positions` and `network.links`. Invalid input is rejected with the original crosswalk 422 error.
- Crossing removal prunes the corresponding visual links and coordinates.
- Camera status and selected-source-only crosswalk region counts are shown, without extra inference, fabricated multi-camera counts or operational signal actions.
- Retain existing legacy junction/source topology tools under a collapsed advanced panel; existing traffic-network routes, intersection data and signal/controller behavior remain unchanged.
- Old Crosswalk schema-1 records without `network` remain valid, with no automatic migration.

Run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1"` from the repository root (full suite). Check add/save crossing → Network node, link A edge 2 to B edge 4, drag/save/reload, remove link/crossing, camera status/AI provenance, Advanced junction configuration, Windows frontend build and live backend smoke. Candidate awaits owner PASS.
