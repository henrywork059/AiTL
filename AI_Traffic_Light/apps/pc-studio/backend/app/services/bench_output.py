"""Fake-only bench output contract. No hardware, network or signal integration."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable

MAX_LEASE_MS = 2000
ACK_TIMEOUT_MS = 100
DEMO_CAPABILITY = "demo_indicator"


@dataclass(frozen=True)
class BenchCommand:
    command_id: int
    capability: str
    duration_ms: int


@dataclass(frozen=True)
class BenchAck:
    command_id: int
    accepted: bool
    latency_ms: int


class FakeBenchAdapter:
    """In-memory stand-in only. An expired lease is never reported as active."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self.connected = False
        self.generation = 0
        self.ack_mode = "ok"  # Test-only fault injection: missing, rejected, wrong_id, late.
        self._expires: float | None = None

    def connect(self) -> None:
        self.generation += 1
        self.off()
        self.connected = True

    def off(self) -> None:
        self._expires = None

    def disconnect(self) -> None:
        self.generation += 1
        self.off()
        self.connected = False

    @property
    def active(self) -> bool:
        if not self.connected or (self._expires is not None and self._clock() >= self._expires):
            self.off()
        return self._expires is not None

    def apply(self, command: BenchCommand, deadline: float) -> BenchAck | None:
        if (not self.connected or command.capability != DEMO_CAPABILITY
                or type(command.duration_ms) is not int or not 1 <= command.duration_ms <= MAX_LEASE_MS
                or self._clock() >= deadline):
            return BenchAck(command.command_id, False, 0)
        if self.ack_mode == "rejected":
            return BenchAck(command.command_id, False, 0)
        self._expires = min(deadline, self._clock() + command.duration_ms / 1000)
        if self.ack_mode == "missing":
            return None
        if self.ack_mode == "wrong_id":
            return BenchAck(command.command_id + 1, True, 0)
        if self.ack_mode == "late":
            return BenchAck(command.command_id, True, ACK_TIMEOUT_MS + 1)
        return BenchAck(command.command_id, True, 0)


class BenchOutputController:
    """Explicitly armed fake adapter with fail-closed lease/acknowledgment checks.

    Authorization is a local test-harness gate, NOT physical hardware permission.
    Watchdog expiry is evaluated on every operation and explicit watchdog tick.
    No background worker or physical driver is created.
    """

    def __init__(self, *, enabled: bool = False, clock: Callable[[], float] = monotonic,
                 adapter: FakeBenchAdapter | None = None) -> None:
        if adapter is not None and type(adapter) is not FakeBenchAdapter:
            raise TypeError("Only the fake bench adapter is allowed")
        self._clock = clock
        self._adapter = adapter if adapter is not None else FakeBenchAdapter(clock)
        self._enabled = enabled is True
        self._armed = False
        self._generation = self._adapter.generation
        self._deadline: float | None = None
        self._sequence = 0
        self._reason = "disabled" if not self._enabled else "not_armed"
        self._lock = RLock()
        self._adapter.off()

    def _safe_off(self, reason: str) -> None:
        self._adapter.off()
        self._armed = False
        self._generation = self._adapter.generation
        self._deadline = None
        self._reason = reason

    def watchdog_tick(self) -> None:
        with self._lock:
            if not self._enabled or not self._adapter.connected:
                self._safe_off("disabled" if not self._enabled else "disconnected")
            elif self._generation != self._adapter.generation:
                self._safe_off("connection_changed")
            elif self._deadline is not None and (self._clock() >= self._deadline or not self._adapter.active):
                self._safe_off("lease_expired")

    def arm(self, *, authorized: bool = False) -> bool:
        with self._lock:
            self.watchdog_tick()
            if not self._enabled or authorized is not True or not self._adapter.connected:
                self._safe_off("authorization_required" if self._enabled and self._adapter.connected else self._reason)
                return False
            self._safe_off("armed")
            self._armed = True
            return True

    def request(self, capability: str, duration_ms: int) -> BenchAck | None:
        with self._lock:
            self.watchdog_tick()
            if not self._armed:
                return None
            if (capability != DEMO_CAPABILITY or type(duration_ms) is not int
                    or not 1 <= duration_ms <= MAX_LEASE_MS or self._deadline is not None):
                self._safe_off("invalid_or_overlapping_command")
                return None
            self._sequence += 1
            command = BenchCommand(self._sequence, capability, duration_ms)
            start = self._clock()
            deadline = start + duration_ms / 1000
            try:
                ack = self._adapter.apply(command, deadline)
            except Exception:
                self._safe_off("adapter_error")
                return None
            elapsed_ms = (self._clock() - start) * 1000
            if (not isinstance(ack, BenchAck) or ack.command_id != command.command_id
                    or ack.accepted is not True or not 0 <= ack.latency_ms <= ACK_TIMEOUT_MS
                    or not 0 <= elapsed_ms <= ACK_TIMEOUT_MS or self._clock() >= deadline
                    or not self._adapter.connected or not self._adapter.active):
                self._safe_off("ack_failed_or_timeout")
                return None
            self._deadline = deadline
            self._reason = "active_fake_lease"
            return ack

    def off(self) -> None:
        with self._lock:
            self._safe_off("explicit_off")

    def disconnect(self) -> None:
        with self._lock:
            self._adapter.disconnect()
            self._safe_off("disconnected")

    def status(self) -> dict:
        with self._lock:
            self.watchdog_tick()
            return {"enabled": self._enabled, "armed": self._armed,
                    "connected": self._adapter.connected, "active": self._armed and self._adapter.active,
                    "reason": self._reason, "capability": DEMO_CAPABILITY,
                    "physical_output_allowed": False, "adapter": "fake", "provenance": "illustrative/synthetic"}
