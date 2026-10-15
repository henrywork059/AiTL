# Patch 0_5_4 — Independent camera counting regions

Candidate `0_5_4`, previous candidate `0_5_3`, accepted baseline `0_5_0`.

The Region Editor now creates camera-side-scoped regions with independent geometry, name and backend ID, while preserving old shared regions. Save regions uses existing atomic persistence. Active-camera detector counts are published per region and class in `crosswalk_region_counts` without altering signal decisions or implying simultaneous multi-camera inference.

Run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -ChangedTests` and validate frontend build, persistence and live counts. Windows PASS pending.
