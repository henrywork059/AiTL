# Patch 0_5_55 — Device setup and connection workflow

Candidate `0_5_55`; previous candidate `0_5_54`; accepted baseline `0_5_0`; roadmap Update 11 / H06. Working branch `feature/interactive-3d-simulation`.

## Changes

The previous connection UI could overwrite an action result with an older polling response, continue to use top-level active-camera data when editing another saved source, and treat an unreachable initially unconfigured ESP as merely saved. The previous manager could also combine A's refreshed session fields with B's selected identity if selection changed while A's HTTP status request was in flight.

- In `RemoteCameraManager.status()`, perform the potentially blocking existing status probe outside the registry lock, then acquire a coherent local selected profile/session/cache snapshot and per-source summaries. No network I/O is added under the registry lock. A selection change during the probe cannot attach A's session diagnostics to B.
- Preserve the failed connection probe's error in the corresponding session without assigning an unverified host or reporting a configured connection. The per-camera capability contract classifies a failed unconfigured connection as error (not merely saved); successful explicit retry clears the error. No automatic stream start or firmware changes.
- Validate literal private-LAN IPv4 addresses, duplicate saved hosts/IDs, source ID syntax, supported frame sizes, and integer setting ranges in the camera setup form before Save/Connect/Start. The backend's existing authoritative validation remains unchanged. New-camera default IDs avoid existing saved IDs.
- Show source-specific status and guidance (waiting, stale, reconnecting, paused, error, reachable, connected), distinguish stream request from received fresh images, retain a saved profile after a failed probe and expose explicit Retry connection. Stop the active stream before reconnecting; existing automatic recovery remains unchanged. On status polling failure, display an actionable backend error instead of a live claim.
- Use an action epoch and synchronous busy guard to discard stale poll responses, guard selected-source Start/Stop/Disconnect actions using the current UI snapshot, and hide the Settings preview if the selected source is not active or its physical frame is not fresh. A post-action pipeline refresh error is not reported as a failed device action.

The existing routes, response envelopes, registry V1 file, wire protocol, signal safety, control permissions, and public-road output restrictions are unchanged. This does not provide cross-client command transactions: existing selected-source control APIs still operate on backend selection at request processing time; another browser can change selection between a UI check and a command. The status snapshot fix is source-identity coherence, not a guarantee that all transport measurements are simultaneous.

## Validation

Added `scripts/test_v0555_camera_setup.py`: real manager/service with fake HTTP responses, invalid/private IP and settings rejection, duplicate IP, saved unreachable profile, explicit retry, restart and deterministic selected-source refresh race, deletion and disconnect. Extended `scripts/test_camera_settings_page_structure.py` for validation, retry, selection guard, poll epoch and stale preview wiring. These are synthetic/software-only tests. Full CI is to be verified on the published commit; no actual ESP hardware, Windows application UI or network endurance measurements were performed in the agent environment.

## Owner acceptance

From repo root in PowerShell:

```powershell
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Verify invalid addresses/duplicate IDs/settings show clear validation, an unplugged ESP remains saved with an error, retry succeeds after restoring power/network, Start Stream does not claim fresh frames before they arrive, stale/disconnected previews stop, switching A/B never displays or commands the wrong source in a single UI, and saved profiles restore after restart. Owner PASS remains required. Next Update 12 / H07: disabled-by-default bench output abstraction, fake adapter only; no physical actuation.
