# Patch 0_5_45 — ESP TCP socket-open cancellation

Candidate `0_5_45`, previous `0_5_44`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Roadmap [Update 01 / H02](ROADMAP.md#4a-numbered-update-by-update-implementation-queue).

## Root cause

The receive worker checks its stop state before opening the socket, but the blocking opener can finish after stop/restart or entry into simulation. The previous code published that socket and updated connection metadata unconditionally, then unconditionally cleared connected status in finally. A delayed retired opener could overwrite a replacement stream.

## Change

After a blocking TCP open returns, recheck cancellation, worker event identity, streaming intent and simulation mode before publishing the socket or connection status. The existing finally block closes the returned socket and clears connection status only when it owns the active socket. This prevents a cancelled opener from replacing a new connection. Ordinary open, read and reconnect behavior, firmware, TCP framing, API shapes and signal behavior remain unchanged.

## Validation and limitations

Isolated execution of the exact retrieved `_run` method with injected opener, consumer and operating state: original 2/5, patched 5/5 (stop, restart, simulation switch, normal open, reconnect). Direct clone unavailable because DNS resolution failed; full-module regression and repository CI were not run locally. Owner Windows/ESP PASS pending.

The repository regression is `scripts/test_v0545_tcp_open_cancellation.py`. This patch is scoped to successful socket returns and owned-socket cleanup. Retired-worker exceptions, recovery calls and other lifecycle races remain the next audit (Update 02); no claim of complete cancellation atomicity.

