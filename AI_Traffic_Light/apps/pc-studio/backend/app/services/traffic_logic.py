from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

VALID_PHASES = {
    "vehicle_green",
    "vehicle_yellow",
    "pedestrian_green",
    "pedestrian_flashing",
    "all_red",
}


def validate_traffic_state(state: dict) -> None:
    """Validate a traffic state dictionary before returning it to the API."""
    phase = state.get("phase")
    if phase not in VALID_PHASES:
        raise AppError(
            ErrorCode.TRAFFIC_STATE_INVALID,
            details={"phase": phase, "valid_phases": sorted(VALID_PHASES)},
        )


def get_mock_traffic_state() -> dict:
    """Return placeholder traffic-light state.

    Later this should be calculated from:
    - detections
    - zones
    - object tracks
    - pedestrian waiting time
    - vehicle queue length
    """
    state = {
        "phase": "vehicle_green",
        "pedestrians_waiting": 2,
        "pedestrians_crossing": 0,
        "vehicles_waiting": 2,
        "decision": "prepare_pedestrian_green",
        "decision_reason": "Pedestrians are waiting and vehicle queue is moderate.",
        "extension_seconds": 5,
    }
    validate_traffic_state(state)
    logger.debug(
        "Generated mock traffic state",
        extra={"phase": state["phase"], "decision": state["decision"]},
    )
    return state
