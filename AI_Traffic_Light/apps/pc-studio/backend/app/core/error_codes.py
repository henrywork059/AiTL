from enum import Enum


class ErrorCode(str, Enum):
    """Stable project error codes.

    Keep this file aligned with docs/ERROR_CODES.md.
    """

    UNKNOWN_ERROR = "ATL-COMMON-000"

    API_REQUEST_FAILED = "ATL-API-001"
    INVALID_REQUEST = "ATL-API-002"
    TEMPLATE_ROUTE_NOT_IMPLEMENTED = "ATL-API-003"

    CONFIG_MISSING = "ATL-CONFIG-001"
    SETTINGS_READ_FAILED = "ATL-CONFIG-002"
    SETTINGS_WRITE_FAILED = "ATL-CONFIG-003"

    CAMERA_NOT_CONNECTED = "ATL-CAMERA-001"
    CAMERA_FRAME_READ_FAILED = "ATL-CAMERA-002"
    CAMERA_SOURCE_INVALID = "ATL-CAMERA-003"
    CAMERA_STREAM_NOT_STARTED = "ATL-CAMERA-004"
    CAMERA_FRAME_TOO_LARGE = "ATL-CAMERA-005"
    CAMERA_FRAME_TYPE_UNSUPPORTED = "ATL-CAMERA-006"
    CAMERA_FRAME_INVALID = "ATL-CAMERA-007"

    MODEL_NOT_LOADED = "ATL-DETECT-001"
    INFERENCE_FAILED = "ATL-DETECT-002"
    INFERENCE_SOURCE_MISSING = "ATL-DETECT-003"
    INFERENCE_RESULT_INVALID = "ATL-DETECT-004"

    ZONE_CONFIG_INVALID = "ATL-ZONE-001"
    ZONE_NOT_FOUND = "ATL-ZONE-002"
    ZONE_SAVE_FAILED = "ATL-ZONE-003"

    TRAFFIC_STATE_INVALID = "ATL-TRAFFIC-001"
    TRAFFIC_RULE_INVALID = "ATL-TRAFFIC-002"
    TRAFFIC_DECISION_FAILED = "ATL-TRAFFIC-003"
    TRAFFIC_HISTORY_READ_FAILED = "ATL-TRAFFIC-004"
    TRAFFIC_HISTORY_WRITE_FAILED = "ATL-TRAFFIC-005"
    TRAFFIC_HISTORY_CLEAR_FAILED = "ATL-TRAFFIC-006"

    DATASET_WRITE_FAILED = "ATL-DATASET-001"
    DATASET_READ_FAILED = "ATL-DATASET-002"
    DATASET_ITEM_NOT_FOUND = "ATL-DATASET-003"
    DATASET_LABEL_INVALID = "ATL-DATASET-004"
    DATASET_TRAINING_NOT_READY = "ATL-DATASET-005"
    DATASET_BUILD_FAILED = "ATL-DATASET-006"
    DATASET_DELETE_FAILED = "ATL-DATASET-007"

    TRAINING_NOT_READY = "ATL-TRAIN-001"
    TRAINING_CONFIG_INVALID = "ATL-TRAIN-002"
    TRAINING_RUN_FAILED = "ATL-TRAIN-003"

    MODEL_REGISTRY_READ_FAILED = "ATL-MODEL-001"
    MODEL_EXPORT_FAILED = "ATL-MODEL-002"
    MODEL_VERSION_NOT_FOUND = "ATL-MODEL-003"
    MODEL_DELETE_FAILED = "ATL-MODEL-004"

    LOG_READ_FAILED = "ATL-LOG-001"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.UNKNOWN_ERROR: "Unexpected backend error.",
    ErrorCode.API_REQUEST_FAILED: "API request failed.",
    ErrorCode.INVALID_REQUEST: "The request is invalid.",
    ErrorCode.TEMPLATE_ROUTE_NOT_IMPLEMENTED: "This route is a template placeholder and is not implemented yet.",
    ErrorCode.CONFIG_MISSING: "Required configuration is missing.",
    ErrorCode.SETTINGS_READ_FAILED: "Failed to read settings.",
    ErrorCode.SETTINGS_WRITE_FAILED: "Failed to write settings.",
    ErrorCode.CAMERA_NOT_CONNECTED: "Camera is not connected.",
    ErrorCode.CAMERA_FRAME_READ_FAILED: "Failed to read a camera frame.",
    ErrorCode.CAMERA_SOURCE_INVALID: "Camera source is invalid.",
    ErrorCode.CAMERA_STREAM_NOT_STARTED: "Camera stream has not been started.",
    ErrorCode.CAMERA_FRAME_TOO_LARGE: "Camera frame is too large.",
    ErrorCode.CAMERA_FRAME_TYPE_UNSUPPORTED: "Camera frame type is unsupported.",
    ErrorCode.CAMERA_FRAME_INVALID: "Camera frame is invalid.",
    ErrorCode.MODEL_NOT_LOADED: "Detection model is not loaded.",
    ErrorCode.INFERENCE_FAILED: "Detection inference failed.",
    ErrorCode.INFERENCE_SOURCE_MISSING: "Inference source is missing.",
    ErrorCode.INFERENCE_RESULT_INVALID: "Inference result is invalid.",
    ErrorCode.ZONE_CONFIG_INVALID: "Zone configuration is invalid.",
    ErrorCode.ZONE_NOT_FOUND: "Zone was not found.",
    ErrorCode.ZONE_SAVE_FAILED: "Failed to save zone configuration.",
    ErrorCode.TRAFFIC_STATE_INVALID: "Traffic state is invalid.",
    ErrorCode.TRAFFIC_RULE_INVALID: "Traffic rule is invalid.",
    ErrorCode.TRAFFIC_DECISION_FAILED: "Traffic decision failed.",
    ErrorCode.TRAFFIC_HISTORY_READ_FAILED: "Failed to read traffic history.",
    ErrorCode.TRAFFIC_HISTORY_WRITE_FAILED: "Failed to write traffic history.",
    ErrorCode.TRAFFIC_HISTORY_CLEAR_FAILED: "Failed to clear traffic history.",
    ErrorCode.DATASET_WRITE_FAILED: "Failed to write dataset item.",
    ErrorCode.DATASET_READ_FAILED: "Failed to read dataset item.",
    ErrorCode.DATASET_ITEM_NOT_FOUND: "Dataset item was not found.",
    ErrorCode.DATASET_LABEL_INVALID: "Dataset label data is invalid.",
    ErrorCode.DATASET_TRAINING_NOT_READY: "The labeled dataset is not ready for a train/validation build.",
    ErrorCode.DATASET_BUILD_FAILED: "Failed to build the managed training dataset.",
    ErrorCode.DATASET_DELETE_FAILED: "Failed to delete the selected dataset capture.",
    ErrorCode.TRAINING_NOT_READY: "Training prerequisites are not ready.",
    ErrorCode.TRAINING_CONFIG_INVALID: "Training configuration is invalid.",
    ErrorCode.TRAINING_RUN_FAILED: "Training run failed.",
    ErrorCode.MODEL_REGISTRY_READ_FAILED: "Failed to read model registry.",
    ErrorCode.MODEL_EXPORT_FAILED: "Failed to export model package.",
    ErrorCode.MODEL_VERSION_NOT_FOUND: "Model version was not found.",
    ErrorCode.MODEL_DELETE_FAILED: "Failed to delete the selected model.",
    ErrorCode.LOG_READ_FAILED: "Failed to read logs.",
}


def default_message(code: ErrorCode) -> str:
    """Return the default human-readable message for an error code."""
    return ERROR_MESSAGES.get(code, "Unexpected project error.")
