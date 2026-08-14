from pydantic import BaseModel, Field
from typing import Literal


class Detection(BaseModel):
    id: str
    class_id: int
    class_name: str
    confidence: float = Field(ge=0, le=1)
    box_xyxy: list[int]


class DetectionFrame(BaseModel):
    frame_id: str
    source_id: str
    image_width: int
    image_height: int
    timestamp_ms: int
    detections: list[Detection]


class Zone(BaseModel):
    id: str
    type: str
    label: str
    polygon: list[list[int]]


class TrafficState(BaseModel):
    phase: Literal[
        "vehicle_green",
        "vehicle_yellow",
        "pedestrian_green",
        "pedestrian_flashing",
        "all_red",
    ]
    pedestrians_waiting: int
    pedestrians_crossing: int
    vehicles_waiting: int
    decision: str
    decision_reason: str
    extension_seconds: int = 0


class CaptureFrameRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=64)
    quality_tag: Literal["unreviewed", "useful", "bad"] = "unreviewed"
    note: str = Field(default="", max_length=500)


class DatasetLabelBoxRequest(BaseModel):
    class_id: int = Field(ge=0, le=1000)
    box_xyxy: tuple[float, float, float, float]


class SaveCaptureLabelsRequest(BaseModel):
    labels: list[DatasetLabelBoxRequest] = Field(default_factory=list, max_length=500)


class BuildTrainingDatasetRequest(BaseModel):
    validation_fraction: float = Field(default=0.2, gt=0, lt=0.5)


class TrainingStartRequest(BaseModel):
    dataset_yaml: str = Field(default="yolo/data.yaml", min_length=5, max_length=240)
    base_model: str = Field(default="yolo26n.pt", min_length=4, max_length=80)
    epochs: int = Field(default=10, ge=1, le=300)
    image_size: int = Field(default=640, ge=64, le=2048)
    batch: int = Field(default=8, ge=1, le=128)
    device: str = Field(default="cpu", min_length=1, max_length=32)
