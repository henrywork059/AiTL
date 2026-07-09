from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class YoloDetectionService:
    """Placeholder for future YOLO detection integration.

    Planned responsibilities:
    - load pretrained model
    - run inference on frame
    - filter target classes
    - return DetectionFrame schema

    Keep this service small. Split model loading, preprocessing, postprocessing,
    and output conversion into separate helper modules when real YOLO code is added.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path
        self.is_loaded = False
        logger.info("YOLO placeholder service created", extra={"model_path": model_path})

    def load(self) -> None:
        logger.warning(
            "YOLO load requested before implementation",
            extra={"error_code": ErrorCode.MODEL_NOT_LOADED.value, "model_path": self.model_path},
        )
        raise AppError(
            ErrorCode.MODEL_NOT_LOADED,
            "YOLO loading will be added in a later version.",
            status_code=501,
            details={"model_path": self.model_path},
        )

    def predict(self, frame):
        logger.warning(
            "YOLO prediction requested before implementation",
            extra={"error_code": ErrorCode.INFERENCE_FAILED.value},
        )
        raise AppError(
            ErrorCode.INFERENCE_FAILED,
            "YOLO inference will be added in a later version.",
            status_code=501,
        )
