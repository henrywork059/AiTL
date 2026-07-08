def get_mock_traffic_state() -> dict:
    """Placeholder traffic-light state.

    Later this should be calculated from:
    - detections
    - zones
    - object tracks
    - pedestrian waiting time
    - vehicle queue length
    """
    return {
        "phase": "vehicle_green",
        "pedestrians_waiting": 2,
        "pedestrians_crossing": 0,
        "vehicles_waiting": 2,
        "decision": "prepare_pedestrian_green",
        "decision_reason": "Pedestrians are waiting and vehicle queue is moderate.",
        "extension_seconds": 5,
    }
