from fastapi import APIRouter

from app.services.traffic_logic import get_mock_traffic_state

router = APIRouter()


@router.get("/state")
def traffic_state() -> dict:
    """Return mock traffic-light state.

    Replace this later with real zone-counting and rule-based decisions.
    """
    return get_mock_traffic_state()
