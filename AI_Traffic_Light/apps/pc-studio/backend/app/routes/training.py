from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def training_status(request: Request) -> dict:
    """Return placeholder training status."""
    data = {
        "training_available": False,
        "active_run_id": None,
        "progress": 0,
        "status": "template_only",
        "note": "Training UI exists only for layout confirmation in 0_1_0. No training process is implemented.",
    }
    logger.info("Training status template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/functions")
def training_functions(request: Request) -> dict:
    """Return planned training/export functions."""
    data = {
        "functions": [
            "select_dataset",
            "select_base_model",
            "set_training_parameters",
            "start_training_run",
            "view_training_logs",
            "evaluate_model",
            "export_runtime_package",
        ]
    }
    logger.info("Training function template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
