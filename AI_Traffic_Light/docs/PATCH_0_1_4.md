# Patch 0_1_4 — Trained-model live inference overlay

## Purpose

Close the next gap in the PC Studio workflow without replacing V013 architecture:

```text
capture → manual label → build YOLO dataset → train → load best.pt → live detection overlay
```

The patch remains PC-side only and within traffic-light simulation/prototype scope.

## Backend implementation

A new `services/inference.py` owns trained-model discovery, model loading, frame decoding, Ultralytics prediction, result conversion, per-frame caching, latency state, and the exact inferred source frame. `routes/inference.py` stays thin.

The service scans:

```text
outputs/training/*/weights/best.pt
```

and orders runs by the `best.pt` modification time. Loading is explicit through the API, while the Live AI page performs one automatic load attempt for the latest model when opened.

Ultralytics prediction uses the current camera image and returns original-image `xyxy` boxes. A 0.10 backend confidence floor avoids rerunning inference every time the frontend display slider moves. Results are cached by `(source_id, frame_number)`.

A small cache of exact image bytes used for recent successful inference results is retained in memory and exposed by source ID/frame number at `/api/inference/frame`. This prevents a moving simulation from advancing to a newer frame between inference and overlay rendering.

## API additions

```text
GET  /api/inference/status
POST /api/inference/load-latest
POST /api/inference/unload
GET  /api/inference/detections
GET  /api/inference/frame
```

JSON endpoints use standard project envelopes and request IDs. The binary inferred-frame endpoint uses an `X-Request-ID` header.

## Frontend implementation

**Live AI** now:

- uses the current receiver/simulation image when available;
- auto-loads the newest trained model when possible;
- exposes reload-latest and unload controls;
- polls live detections serially rather than stacking concurrent requests;
- overlays class/confidence boxes in original camera coordinates;
- filters displayed detections with the existing confidence threshold concept;
- shows active model, latest model, frame number, and measured inference latency;
- preserves the older mock scene as fallback when no camera frame is available.

Traffic-light state and zone panels remain mock/prototype displays. V014 does not yet convert live detections into zone counts or live traffic decisions.

## Runtime/data boundary

Trained `.pt` weights, datasets, labels, and training outputs remain local generated data and are excluded from the patch ZIP. The patch contains code/docs/tests only.

## Validation added

`python .\scripts\test_inference_service.py` verifies:

- newest trained `best.pt` discovery;
- fake trained-model loading without an external model download;
- original-coordinate class/confidence box conversion;
- per-frame inference caching;
- exact inferred source-frame retention;
- stable missing/unloaded model errors.

The existing smoke test now also checks `/api/inference/status`.

## Limitations

- A small or poorly labeled training dataset can produce inaccurate or zero detections.
- Live inference throughput depends on PyTorch/Ultralytics device support and model size.
- The backend holds one active model per process and does not implement multi-model comparison or automatic hot-swap after training.
- Automatic labeling, segmentation, model export, live zone counting, and physical traffic-light control are not implemented.
- 0_1_4 is a candidate until the owner completes the acceptance checklist.
