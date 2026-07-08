class YoloDetectionService:
    """Placeholder for future YOLO detection integration.

    Planned responsibilities:
    - load pretrained model
    - run inference on frame
    - filter target classes
    - return DetectionFrame schema

    This is intentionally not implemented in version 1.
    """

    def __init__(self, model_path: str | None = None):
        self.model_path = model_path
        self.is_loaded = False

    def load(self) -> None:
        raise NotImplementedError("YOLO loading will be added in a later version.")

    def predict(self, frame):
        raise NotImplementedError("YOLO inference will be added in a later version.")
