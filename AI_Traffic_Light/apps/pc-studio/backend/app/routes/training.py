from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.models import TrainingStartRequest
from app.services.training import training_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def training_status(request: Request) -> dict:
    """Return optional Ultralytics availability and the current run state."""
    data = training_service.status()
    logger.info("Training status returned", extra={"request_id": request.state.request_id, "status": data["status"]})
    return ok(data, request_id=request.state.request_id)


@router.post("/start")
def start_training(payload: TrainingStartRequest, request: Request) -> dict:
    """Validate and launch one real YOLO training job in a background thread."""
    data = training_service.start(
        dataset_yaml=payload.dataset_yaml,
        base_model=payload.base_model,
        epochs=payload.epochs,
        image_size=payload.image_size,
        batch=payload.batch,
        device=payload.device,
    )
    logger.info(
        "Training start API accepted",
        extra={"request_id": request.state.request_id, "run_id": data["active_run_id"]},
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/functions")
def training_functions(request: Request) -> dict:
    """Return implemented training and planned export functions."""
    data = {
        "functions": [
            "select_dataset",
            "select_base_model",
            "set_training_parameters",
            "start_training_run",
            "view_training_logs",
            "evaluate_model_later",
            "export_runtime_package",
        ]
    }
    logger.info("Training function template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
