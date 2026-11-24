# Patch 0_5_54 — Derived device capability contract

Candidate `0_5_54`, previous `0_5_53`, accepted baseline `0_5_0`, working branch `feature/interactive-3d-simulation`. Roadmap Update 10 / H06.

## Root cause and implementation

The existing saved camera registry owned camera identity and runtime health, but did not offer a reusable typed capability contract. Adding a separate device database or persisting inferred hardware support would duplicate ownership and risk misrepresenting untested physical modules.

The pure `device_capabilities.py` projector now derives a versioned, read-only `device_contract` from each source-qualified saved camera summary. `RemoteCameraManager.status()` adds the projection to each `cameras[]` item and provides the selected camera's contract at top level, or `null` when none is selected. The top-level contract is chosen from the source-qualified summaries, not from independently refreshed selected-camera fields. Existing fields and envelopes are unchanged. Frontend `remoteCameraApi.ts` describes the additive typed fields.

`camera_input` identifies the implemented PC-controlled JPEG input path (or simulation-only source) but reports `available: true` only for a currently streaming, connected, non-stale source with original cached receive-time evidence, or an active simulated source. Saving an IP is not evidence that the ESP is reachable. `lighting_output` and `speaker_output` are explicitly `support: unavailable`, `available: false`; `physical_output_allowed` is always false. Health exposes distinct not-connected, connected, unreachable, reconnecting, waiting-for-frame, streaming, stale, paused, error and simulated/idle states. Simulation reachability/control fields are null, not claims about physical hardware.

The existing `config/remote_cameras.json` V1 schema, normalization, CRUD, connection lifecycle, source generation, cached frames and wire transport are unchanged. No new endpoint, registry, persistent field, active probe, extra JPEG decode or output command. This is a **foundation**, not a general-purpose discovered modular hardware bus or a bench-actuation interface.

## Validation evidence

Actually executed in the current isolated Python environment: `test_v0554_device_capabilities.py` (3/3 pytest functions and direct script) and Python compilation. The pure cases cover 11 ESP states including inconsistent disconnected/streaming evidence, simulated/idle input, source isolation, unknown module rejection, JSON structure and permanently unavailable outputs. The exact projector and pure-test blobs match locally tested file checksums.

Added but not executed against the full repository: `test_v0554_device_registry.py`, covering pre-existing V1 JSON (including ESP profiles with no `kind` field), profile reload/save without new persisted fields, multi-camera selection, transition to live frame availability, simulation saved source and no commands on passive status discovery. This integration regression requires the full repository environment.

Full structure guard, offline suite, TypeScript/build, CI and owner Windows/ESP acceptance were not verified. The previously identified possible selected-status concurrency race in other top-level legacy fields is not fixed by this additive contract; the projected selected contract uses the source-qualified `cameras[]` data.

## Owner acceptance

From the repository root on Windows:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Check two saved cameras with different runtime states, saved profiles after restart, physical disconnect/reconnect, simulation mode, no lighting/speaker capability and no physical output. Owner PASS is required before changing the baseline. Next: roadmap Update 11 / H06 — improve device setup, connection/error workflow and retry behavior.

## CI regression triage — same candidate, no runtime safety relaxation

Push workflow [45424883577](https://github.com/henrywork059/AiTL/actions/runs/45424883577) failed at `test_v0525_camera_diagnostics.py`. The existing test manually injected cached results but did not install the source-lifetime tokens now required by V0548's stale/retired-source guard. Three consecutive candidate push runs exhibited the same legacy test-fixture failure. This does **not** establish a production inference defect.

Corrective follow-up on `0_5_54`: update **only** that regression fixture with explicit source/mode tokens and a controlled source-validity mock for diagnostics formatting, plus an assertion that removing a token makes even a recently timestamped result unavailable. The real `MultiCameraInferenceService` and `RemoteCameraManager.observation_is_current` remain unchanged. The tests in the other V0548 lifecycle scripts continue to cover actual source retirement.

The corrective code needs a new CI run; full Windows/ESP and owner acceptance remain pending. The older workflow failure is not recorded as PASS.
