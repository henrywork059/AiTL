# 0_5_60 — Separate ATL1 transport framing from camera lifecycle

Candidate; roadmap Update 16 / A04. Previous 0_5_59; accepted baseline 0_5_0.

## Implementation

Extract the existing ATL1 packet value, exact-length socket wrapper, encoder and decoder into `camera_tcp_transport.py`. The extracted class/function bodies are unchanged. `RemoteCameraService` imports the same symbols at its existing compatibility and monkeypatch seams; it retains socket opening/configuration, worker ownership, stop/join, cancellation, recovery, control requests and frame publication. `RemoteCameraManager` remains the sole registry/session-selection owner. No new transport, duplicate parser, API change, wire change, physical output or freshness policy change.

## Validation

Three isolated regression groups passed (fragmented framing, socket shutdown, malformed/truncated packets); isolated Python compilation passed. The local test uses the existing 8 MiB frame-size constant in an isolated stub; full checkout could not be cloned because GitHub DNS resolution failed. Full candidate CI, actual ESP throughput/CPU comparison and Windows/ESP owner PASS remain pending. No performance improvement claimed. Previous 0_5_59 CI passed ([run 45518551845](https://github.com/henrywork059/AiTL/actions/runs/45518551845)).

Run `python scripts/test_v0560_tcp_transport.py`, `python scripts/test_remote_camera_session.py`, `python scripts/test_remote_camera_multi.py`, `python scripts/test_remote_camera_control_resilience.py`, `python scripts/test_v0544_tcp_read_cancellation.py`, `python scripts/test_v0545_tcp_open_cancellation.py`, `python scripts/test_v0546_worker_retirement.py` and `python scripts/test_v0552_camera_transport_diagnostics.py`. Compare original and new candidates with the same ESP, configuration, LAN, duration and hardware using the existing endurance recorder. Record achieved FPS and PC CPU on the same measurement basis; no bench results yet. Physical lighting/speaker remain blocked. Next Update 17 / A03, subject to CI and roadmap gates.
