from enum import Enum


class ErrorCode(str, Enum):
    """Stable project error codes.

    Keep this file aligned with docs/ERROR_CODES.md.
    """

    UNKNOWN_ERROR = "ATL-COMMON-000"

    API_REQUEST_FAILED = "ATL-API-001"
    INVALID_REQUEST = "ATL-API-002"

    CONFIG_MISSING = "ATL-CONFIG-001"

    CAMERA_NOT_CONNECTED = "ATL-CAMERA-001"
    CAMERA_FRAME_READ_FAILED = "ATL-CAMERA-002"

    MODEL_NOT_LOADED = "ATL-DETECT-001"
    INFERENCE_FAILED = "ATL-DETECT-002"

    ZONE_CONFIG_INVALID = "ATL-ZONE-001"

    TRAFFIC_STATE_INVALID = "ATL-TRAFFIC-001"

    DATASET_WRITE_FAILED = "ATL-DATASET-001"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.UNKNOWN_ERROR: "Unexpected backend error.",
    ErrorCode.API_REQUEST_FAILED: "API request failed.",
    ErrorCode.INVALID_REQUEST: "The request is invalid.",
    ErrorCode.CONFIG_MISSING: "Required configuration is missing.",
    ErrorCode.CAMERA_NOT_CONNECTED: "Camera is not connected.",
    ErrorCode.CAMERA_FRAME_READ_FAILED: "Failed to read a camera frame.",
    ErrorCode.MODEL_NOT_LOADED: "Detection model is not loaded.",
    ErrorCode.INFERENCE_FAILED: "Detection inference failed.",
    ErrorCode.ZONE_CONFIG_INVALID: "Zone configuration is invalid.",
    ErrorCode.TRAFFIC_STATE_INVALID: "Traffic state is invalid.",
    ErrorCode.DATASET_WRITE_FAILED: "Failed to write dataset item.",
}


def default_message(code: ErrorCode) -> str:
    """Return the default human-readable message for an error code."""
    return ERROR_MESSAGES.get(code, "Unexpected project error.")
