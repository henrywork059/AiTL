# V0564 — Simulation engine evaluation foundation

Candidate `0_5_64`; previous `0_5_63`; accepted baseline `0_5_0`; Update 20 / S01.

## Implementation

Update 20 / S01 documents the conditional choice of Eclipse SUMO (external process, eventual single-client TraCI adapter) for microscopic traffic and Three.js (WebGL renderer) for presentation. Added a standalone standard-library Python evaluation harness that generates a synthetic four-arm signalized junction and identical seeded vehicle/pedestrian demand, runs two optional SUMO CLI trials and compares normalized position traces. The current simulator, protected signal controller, camera routes, existing network experiment service and production renderer remain unchanged. No SUMO, TraCI, Three.js or other new dependency installed or adopted.

[Evaluation decision, protocol and upstream references](SIMULATION_ENGINE_EVALUATION.md).

## Validation

Actual local evidence (25 November 2026): Python 3.13.5, Linux x86_64; three offline unittest cases passed and both Python files compiled. The real harness ran and returned exit 2 / blocked with zero trials because sumo and netconvert were absent from PATH; no TraCI, libsumo or CityFlow package installed. GitHub checkout DNS failed; no full local checkout or renderer test. Exact staged Git blobs: harness 448f17187d9c7afcf216438e0915de92f7cb3411, test 81c629182523bd8675d2a5921f0c028d9c754925. Prior full CI passed ([45601046778](https://github.com/henrywork059/AiTL/actions/runs/45601046778)); new CI and owner PASS pending. No measured third-party engine performance or physical validation.

```powershell
# From AI_Traffic_Light, no optional dependencies needed for these checks
python scripts/test_v0564_engine_evaluation.py
python -m py_compile scripts/evaluate_simulation_engine.py scripts/test_v0564_engine_evaluation.py
# Optional: only after vetted SUMO installation, with sumo and netconvert on PATH
python scripts/evaluate_simulation_engine.py --output "$env:TEMP\mesh-sumo-evaluation.json"
```

## Limitations and next gate

Engine choice is conditional, not adoption. Before shadow integration, run the optional smoke scenario on a pinned Windows SUMO distribution and validate pedestrian path/crossing geometry, both traces and error handling. Before dependency adoption, inspect existing npm high-severity findings and proposed dependency tree, verify licenses and versions, and document remediation or explicitly accepted residual risk. Compare matched traffic and render workloads; retain rollback, independent safety rules and no physical actuation. No throughput, CPU/RAM, GPU, latency or safety superiority has been demonstrated. Update 21 can proceed with the existing simulator adapter and deterministic clock without new dependencies; Update 22 must wait for engine and security gates.
