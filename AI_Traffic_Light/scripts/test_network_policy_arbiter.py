from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.network_policy_arbiter import (  # noqa: E402
    POLICY_PRIORITIES,
    arbitrate_network_policy,
    defer_action_for,
)


def _decision(**overrides):
    payload = {
        "incident_hold": False,
        "phase_key": "vehicle_green",
        "pedestrian_waiting": 0,
        "pedestrian_crossing": 0,
        "oldest_pedestrian_wait_seconds": 0.0,
        "pedestrian_max_wait_seconds": 30.0,
        "emergency_priority_active": False,
        "vehicle_class_priority_active": False,
        "cooperation_active": False,
    }
    payload.update(overrides)
    return arbitrate_network_policy(**payload)


def main() -> int:
    incident = _decision(
        incident_hold=True,
        phase_key="pedestrian_flashing",
        pedestrian_waiting=3,
        pedestrian_crossing=1,
        oldest_pedestrian_wait_seconds=45.0,
        emergency_priority_active=True,
        vehicle_class_priority_active=True,
        cooperation_active=True,
    )
    assert incident.owner == "incident_hold"
    assert incident.priority == POLICY_PRIORITIES["incident_hold"]
    assert incident.conflict is True

    crossing = _decision(
        phase_key="pedestrian_flashing",
        pedestrian_waiting=3,
        pedestrian_crossing=1,
        oldest_pedestrian_wait_seconds=45.0,
        emergency_priority_active=True,
        vehicle_class_priority_active=True,
        cooperation_active=True,
    )
    assert crossing.owner == "pedestrian_crossing"
    assert crossing.priority > POLICY_PRIORITIES["emergency_priority"]
    assert defer_action_for(crossing.owner) == "protect_pedestrian_service"

    emergency = _decision(
        pedestrian_waiting=2,
        oldest_pedestrian_wait_seconds=45.0,
        emergency_priority_active=True,
        vehicle_class_priority_active=True,
        cooperation_active=True,
    )
    assert emergency.owner == "emergency_priority"
    assert [item.owner for item in emergency.candidates][:2] == ["emergency_priority", "pedestrian_max_wait"]

    pedestrian = _decision(
        pedestrian_waiting=2,
        oldest_pedestrian_wait_seconds=45.0,
        vehicle_class_priority_active=True,
        cooperation_active=True,
    )
    assert pedestrian.owner == "pedestrian_max_wait"
    assert defer_action_for(pedestrian.owner) == "defer_for_pedestrian_max_wait"

    class_priority = _decision(vehicle_class_priority_active=True, cooperation_active=True)
    assert class_priority.owner == "vehicle_class_priority"
    assert class_priority.conflict is True
    assert defer_action_for(class_priority.owner) == "defer_for_vehicle_class_priority"

    cooperation = _decision(cooperation_active=True)
    assert cooperation.owner == "network_cooperation"
    assert cooperation.conflict is False

    normal = _decision()
    assert normal.owner == "normal_timing"
    assert normal.candidates == ()

    # Waiting pedestrians during an already-active WALK/CLEAR do not become a
    # starvation-prevention owner; the protected service has begun.
    service_active = _decision(
        phase_key="pedestrian_green",
        pedestrian_waiting=5,
        oldest_pedestrian_wait_seconds=60.0,
        cooperation_active=True,
    )
    assert service_active.owner == "network_cooperation"

    print("V031 network policy arbiter regression OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
