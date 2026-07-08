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
