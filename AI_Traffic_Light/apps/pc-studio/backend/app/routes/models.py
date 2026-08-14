from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.models import InferenceLoadRequest
from app.services.inference import inference_service
from app.services.model_registry import model_registry_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("")
def model_registry_status(request: Request) -> dict:
    """Return discovered local trained models and default-selection metadata."""
    data = model_registry_service.status(active_model_id=inference_service.status().get("active_model_id"))
    logger.info("Model registry returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/default")
def set_default_model(payload: InferenceLoadRequest, request: Request) -> dict:
    """Set the default trained model used for auto-load in Live AI."""
    if not payload.model_id:
        raise AppError(
            ErrorCode.INVALID_REQUEST,
            "model_id is required for the default-model operation.",
            status_code=422,
        )
    data = model_registry_service.set_default_model(payload.model_id)
    logger.info(
        "Default model set through API",
        extra={"request_id": request.state.request_id, "model_id": payload.model_id},
    )
    return ok(data, request_id=request.state.request_id)


@router.delete("/{model_id}")
def delete_model(model_id: str, request: Request) -> dict:
    """Delete a trained model run directory and unload it if active."""
    data = inference_service.delete_model(model_id)
    logger.info(
        "Trained model deleted through API",
        extra={"request_id": request.state.request_id, "model_id": model_id},
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/functions")
def model_functions(request: Request) -> dict:
    data = {
        "functions": [
            "list_local_trained_models",
            "set_default_model",
            "delete_selected_model",
            "show_active_latest_default_state",
        ]
    }
    logger.info("Model function list returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
