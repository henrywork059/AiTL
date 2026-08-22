from __future__ import annotations

from dataclasses import dataclass
from typing import Any


POLICY_PRIORITIES: dict[str, int] = {
    "incident_hold": 1000,
    "pedestrian_crossing": 900,
    "emergency_priority": 800,
    "pedestrian_max_wait": 700,
    "vehicle_class_priority": 600,
    "network_cooperation": 500,
    "ranked_scenario": 100,
    "normal_timing": 0,
}


@dataclass(frozen=True)
class PolicyCandidate:
    owner: str
    priority: int
    reason: str


@dataclass(frozen=True)
class PolicyArbitration:
    owner: str
    priority: int
    reason: str
    candidates: tuple[PolicyCandidate, ...]

    @property
    def conflict(self) -> bool:
        return len(self.candidates) > 1

    def allows(self, owner: str) -> bool:
        return self.owner == owner

    def as_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "priority": self.priority,
            "reason": self.reason,
            "conflict": self.conflict,
            "candidates": [
                {"owner": item.owner, "priority": item.priority, "reason": item.reason}
                for item in self.candidates
            ],
        }


def arbitrate_network_policy(
    *,
    incident_hold: bool,
    phase_key: str,
    pedestrian_waiting: int,
    pedestrian_crossing: int,
    oldest_pedestrian_wait_seconds: float,
    pedestrian_max_wait_seconds: float,
    emergency_priority_active: bool,
    vehicle_class_priority_active: bool,
    cooperation_active: bool,
) -> PolicyArbitration:
    """Choose one simulation-only timing overlay owner for one intersection tick.

    Ranked scenarios remain the controller-owned base policy. This arbiter owns
    only the higher-level network experiment overlays, ensuring that ordinary
    cooperation/class/pedestrian-starvation/emergency layers do not all mutate
    the same phase duration in one tick merely because of call order.

    Priority order:
      incident hold > active pedestrian crossing > emergency priority >
      pedestrian max-wait > configured class priority > network cooperation.

    The active-crossing guard is deliberately limited to protected pedestrian
    WALK/CLEAR phases. Waiting pedestrians at/above the max-wait threshold are
    a separate starvation-prevention candidate below simulated emergency
    priority but above ordinary class/cooperation advisories.
    """

    candidates: list[PolicyCandidate] = []
    normalized_phase = str(phase_key or "unknown")
    waiting = max(0, int(pedestrian_waiting))
    crossing = max(0, int(pedestrian_crossing))
    oldest = max(0.0, float(oldest_pedestrian_wait_seconds))
    max_wait = max(0.0, float(pedestrian_max_wait_seconds))

    if incident_hold:
        candidates.append(
            PolicyCandidate(
                "incident_hold",
                POLICY_PRIORITIES["incident_hold"],
                "controller incident hold blocks all experiment timing overlays",
            )
        )

    if normalized_phase in {"pedestrian_green", "pedestrian_flashing"} and crossing > 0:
        candidates.append(
            PolicyCandidate(
                "pedestrian_crossing",
                POLICY_PRIORITIES["pedestrian_crossing"],
                "active simulated pedestrian crossing owns local clearance protection",
            )
        )

    if emergency_priority_active:
        candidates.append(
            PolicyCandidate(
                "emergency_priority",
                POLICY_PRIORITIES["emergency_priority"],
                "simulated emergency request is active at this intersection inside the configured lookahead",
            )
        )

    pedestrian_service_active = normalized_phase in {"pedestrian_green", "pedestrian_flashing"}
    if waiting > 0 and oldest + 1e-9 >= max_wait and not pedestrian_service_active:
        candidates.append(
            PolicyCandidate(
                "pedestrian_max_wait",
                POLICY_PRIORITIES["pedestrian_max_wait"],
                "pedestrian wait reached the configured starvation-prevention threshold",
            )
        )

    if vehicle_class_priority_active:
        candidates.append(
            PolicyCandidate(
                "vehicle_class_priority",
                POLICY_PRIORITIES["vehicle_class_priority"],
                "configured regular vehicle class meets the class-priority trigger",
            )
        )

    if cooperation_active:
        candidates.append(
            PolicyCandidate(
                "network_cooperation",
                POLICY_PRIORITIES["network_cooperation"],
                "predicted incoming vehicles meet the configured cooperation trigger",
            )
        )

    if not candidates:
        return PolicyArbitration(
            owner="normal_timing",
            priority=POLICY_PRIORITIES["normal_timing"],
            reason="no higher-level network timing overlay is active",
            candidates=(),
        )

    ordered = tuple(sorted(candidates, key=lambda item: (-item.priority, item.owner)))
    winner = ordered[0]
    return PolicyArbitration(
        owner=winner.owner,
        priority=winner.priority,
        reason=winner.reason,
        candidates=ordered,
    )


def defer_action_for(owner: str) -> str:
    mapping = {
        "incident_hold": "defer_for_incident_hold",
        "pedestrian_crossing": "protect_pedestrian_service",
        "emergency_priority": "defer_for_emergency_priority",
        "pedestrian_max_wait": "defer_for_pedestrian_max_wait",
        "vehicle_class_priority": "defer_for_vehicle_class_priority",
        "network_cooperation": "defer_for_network_cooperation",
    }
    return mapping.get(str(owner), "defer_for_higher_priority_policy")
