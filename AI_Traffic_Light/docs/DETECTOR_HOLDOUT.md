# Update 28C — offline synthetic detector holdout

Use existing `scripts/native_detector_batch.py` with `--model` pointing to trusted local .pt weights and `--holdout-manifest` pointing to an operator-prepared JSON plan. Do not load untrusted checkpoint files; .pt serialization may execute code. No weights or captures should be committed. Use a dedicated offline Python environment with the existing optional training dependency. Explicitly freeze the manifest before viewing outcomes; keep it alongside the report and original capture archive digests.

Manifest fields (schema_version 1):

- `model_sha256`: SHA-256 of the exact model file (lowercase hex).
- `model_provenance`, `training_separation`, `holdout_selection`: nonempty documented declarations; explain source, training/selection and separation limitations.
- `confidence`, `iou_threshold`: numbers in (0,1], equal to command arguments.
- `captures`: object mapping each relative capture.zip path beneath the capture root (forward slashes) to its archive SHA-256. The set must exactly match the discovered archives. Each archive must pass existing qualification and contain its internal integrity manifest.
- `known_training_canonical_pixel_sha256`: array of distinct known training image SHA-256 values of contiguous decoded BGR pixel bytes at the canonical capture dimensions; empty means no known hashes, not proven independent training.
- `criteria`: object with vehicle and pedestrian entries, each containing positive integer min_truth, and min_precision/min_recall in (0,1]. Choose and justify these before evaluation; there are no default acceptance thresholds. Each of the four views must independently meet both kinds' criteria. Missing denominators fail.

Example command (PowerShell from AI_Traffic_Light; substitute your actual predeclared confidence and IoU):

```powershell
python scripts/native_detector_batch.py --capture-root <capture-root> --model <trusted-local-model.pt> --holdout-manifest <plan.json> --confidence 0.1 --iou 0.5 --output <report.json>
```

The numeric command values are examples, not recommended acceptance thresholds. Use actual paths, not angle-bracket placeholders. Exit 2 means declared criteria not met; retain the output instead of retuning on the holdout. Other errors prevent qualification. Exact duplicate canonical pixels and known training overlaps are rejected, but nearby frames and mirrored views remain correlated. The output uses the existing production box converter offline, not the live inference service; no trained detector is qualified merely by running palette or fake-model tests. The result is synthetic raster footprint agreement only, not field accuracy, mAP, physical calibration, public-road safety, or migration authorization. A separate independently justified detector, frozen holdout and actual run are still required.
