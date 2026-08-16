# PC Studio Backend — V023 candidate

FastAPI backend for the local AI Traffic Light prototype.

## Working prototype functions

- receive device JPEG/PNG frames and run the controllable signal-aware synthetic camera;
- persist captures, deletion/labels, managed YOLO datasets, optional local training, trained-model registry, and live inference;
- assign frame-deduplicated prototype track IDs and persist occupancy/flow analytics separately;
- persist camera-aligned traffic regions and two-point counting lines;
- configure validated simulated signal min/base/max timings and Fixed / Adaptive / Test policy modes;
- evaluate bounded adaptive timing rules with priority ordering, persistence, cooldown, demand memory, stale-data fallback, protected phase order, and maximum-cycle limits;
- expose live signal-policy status, rule health/arbitration, dry previews, Test-mode accessibility/incident inputs, incident clearing, adaptive-state reset, and decision-history APIs;
- persist signal policy in `config/signal_rules.json` and runtime decision history in `outputs/signal_rules/decision_history.jsonl`.

The current perception model is not claimed to detect wheelchairs/mobility aids or person-fall incidents. Those conditions are Test-mode inputs until a compatible detector is deliberately added.

Root `AI_Traffic_Light/VERSION` is the canonical release state. Runtime datasets, settings, signal policy, occupancy/flow/signal histories, and trained models are user/runtime data and are excluded from source patches.

This backend is for prototype, simulation, classroom, and supervised testing only. It is not a public-road traffic controller.
