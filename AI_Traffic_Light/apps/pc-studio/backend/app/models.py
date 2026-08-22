from typing import Any, Literal

from pydantic import BaseModel, Field


class Detection(BaseModel):
    id: str
    class_id: int
    class_name: str
    confidence: float = Field(ge=0, le=1)
    box_xyxy: list[int]
    track_id: str | None = None
    track_age_frames: int | None = None


class DetectionFrame(BaseModel):
    frame_id: str
    source_id: str
    image_width: int
    image_height: int
    timestamp_ms: int
    source_frame_number: int | None = None
    detections: list[Detection]


class Zone(BaseModel):
    id: str
    type: Literal["pedestrian_waiting", "crossing", "vehicle_queue", "counting_region", "counting_line", "ignore"]
    label: str
    polygon: list[list[int]]


class SaveZonesRequest(BaseModel):
    zones: list[Zone] = Field(default_factory=list, max_length=32)


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
    pedestrians_total: int = 0
    vehicles_total: int = 0
    decision: str
    decision_reason: str
    extension_seconds: int = 0
    data_source: str | None = None
    evaluated_at_ms: int | None = None
    source_timestamp_ms: int | None = None
    evaluated_frame_number: int | None = None
    zone_counts: dict[str, int] = Field(default_factory=dict)
    zone_class_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    region_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    tracking: dict = Field(default_factory=dict)
    recommended_phase: str | None = None
    recommended_decision: str | None = None
    recommended_decision_reason: str | None = None
    signal_policy: dict[str, Any] | None = None
    intersection_id: str = "intersection_main"
    observation_provenance: Literal["ai_detection", "simulation", "manual_test", "unavailable"] = "unavailable"
    network_context: dict[str, Any] = Field(default_factory=dict)
    decision_context: dict[str, Any] = Field(default_factory=dict)
    prototype_only: bool = True


class CameraSimulationSettingsRequest(BaseModel):
    density: Literal["light", "normal", "busy"] | None = None
    paused: bool | None = None


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
    patience: int = Field(default=5, ge=1, le=100)


class RuntimeSettingsRequest(BaseModel):
    default_confidence: float = Field(default=0.10, ge=0.01, le=1.0)
    live_poll_interval_ms: int = Field(default=500, ge=250, le=5000)
    training_patience: int = Field(default=5, ge=1, le=100)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class SignalRulesConfigRequest(BaseModel):
    config: dict[str, Any]


class IntersectionNetworkConfigRequest(BaseModel):
    config: dict[str, Any]


class SignalTestInputsRequest(BaseModel):
    pedestrians_waiting: int | None = Field(default=None, ge=0, le=500)
    pedestrians_crossing: int | None = Field(default=None, ge=0, le=500)
    vehicles_waiting: int | None = Field(default=None, ge=0, le=500)
    mobility_assistance: bool | None = None
    incident_person_fallen: bool | None = None


class SignalRulesPreviewRequest(BaseModel):
    phase_key: Literal[
        "vehicle_green",
        "vehicle_yellow",
        "all_red_to_pedestrian",
        "pedestrian_green",
        "pedestrian_flashing",
        "all_red_to_vehicle",
    ] = "vehicle_green"
    pedestrians_waiting: int = Field(default=0, ge=0, le=500)
    pedestrians_crossing: int = Field(default=0, ge=0, le=500)
    vehicles_waiting: int = Field(default=0, ge=0, le=500)
    pedestrian_wait_seconds: float = Field(default=0, ge=0, le=3600)
    vehicle_wait_seconds: float = Field(default=0, ge=0, le=3600)
    crossing_dwell_seconds: float = Field(default=0, ge=0, le=3600)
    mobility_assistance: bool = False
    incident_person_fallen: bool = False
    zone_class_counts: dict[str, dict[str, int]] = Field(default_factory=dict)


class SimulationExperimentRunRequest(BaseModel):
    duration_seconds: int = Field(default=300, ge=30, le=1800)
    density: Literal["light", "normal", "busy"] = "normal"
    seed: int = Field(default=25025, ge=0, le=2_147_483_647)
    sample_interval_seconds: int = Field(default=1, ge=1, le=10)
    profile: str | None = Field(default=None, min_length=1, max_length=64)
    label: str = Field(default="", max_length=80)


class NetworkSimulationExperimentRunRequest(BaseModel):
    duration_seconds: int = Field(default=300, ge=30, le=1800)
    density: Literal["light", "normal", "busy"] = "normal"
    seed: int = Field(default=27027, ge=0, le=2_147_483_647)
    sample_interval_seconds: int = Field(default=1, ge=1, le=10)
    profile: str | None = Field(default=None, min_length=1, max_length=64)
    label: str = Field(default="", max_length=80)
    link_id: str | None = Field(default=None, min_length=1, max_length=64)
    transfer_share_percent: int = Field(default=70, ge=0, le=100)
    cooperation_lookahead_seconds: float = Field(default=12.0, ge=1.0, le=60.0)
    cooperation_max_extension_seconds: float = Field(default=5.0, ge=0.0, le=20.0)
    cooperation_min_incoming_vehicles: int = Field(default=1, ge=1, le=20)


class InferenceLoadRequest(BaseModel):
    model_id: str | None = Field(default=None, min_length=1, max_length=120)
