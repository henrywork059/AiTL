# Error Codes

Stable project errors used by the current prototype APIs.

## Dataset

- `ATL-DATASET-001` — dataset write failed
- `ATL-DATASET-002` — dataset read failed
- `ATL-DATASET-003` — dataset item/capture not found
- `ATL-DATASET-004` — dataset label invalid
- `ATL-DATASET-005` — labeled dataset not ready for training build
- `ATL-DATASET-006` — managed YOLO dataset build failed
- `ATL-DATASET-007` — captured image/metadata/label deletion failed

## Inference

- `ATL-DETECT-001` — model not loaded
- `ATL-DETECT-002` — inference failed
- `ATL-DETECT-003` — inference source missing
- `ATL-DETECT-004` — inference result invalid

## Zones

- `ATL-ZONE-001` — zone configuration invalid
- `ATL-ZONE-002` — requested zone/counting region/counting line not found
- `ATL-ZONE-003` — zone save failed

## Traffic / analytics / experiments

- `ATL-TRAFFIC-001` — traffic state invalid
- `ATL-TRAFFIC-002` — traffic signal/scenario configuration invalid (including scenario id/rank, condition source/operator/threshold, phase targets, actions, and timing bounds)
- `ATL-TRAFFIC-003` — traffic decision failed
- `ATL-TRAFFIC-004` — persisted traffic history read failed
- `ATL-TRAFFIC-005` — traffic history sample write/compaction failed
- `ATL-TRAFFIC-006` — traffic history clear failed
- `ATL-TRAFFIC-007` — persisted traffic flow/event read failed
- `ATL-TRAFFIC-008` — traffic flow/event write or compaction failed
- `ATL-TRAFFIC-009` — traffic flow/event clear failed
- `ATL-TRAFFIC-010` — persisted simulation experiment read/not-found failure
- `ATL-TRAFFIC-011` — simulation experiment write failed
- `ATL-TRAFFIC-012` — simulation experiment delete failed

## Models

- `ATL-MODEL-001` — model registry read failed
- `ATL-MODEL-002` — model export failed (reserved)
- `ATL-MODEL-003` — model version not found
- `ATL-MODEL-004` — model delete failed

## Configuration

- `ATL-CONFIG-001` — required configuration missing
- `ATL-CONFIG-002` — settings read failed
- `ATL-CONFIG-003` — settings write failed
