from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.routes.camera import router as camera_router
from app.routes.dataset import router as dataset_router
from app.routes.health import router as health_router
from app.routes.inference import router as inference_router
from app.routes.logs import router as logs_router
from app.routes.mock import router as mock_router
from app.routes.models import router as models_router
from app.routes.settings import router as settings_router
from app.routes.smoke import router as smoke_router
from app.routes.template import router as template_router
from app.routes.traffic import router as traffic_router
from app.routes.training import router as training_router
from app.routes.zones import router as zones_router

APP_VERSION = "0_1_7"
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the PC Studio backend app.

    Keep this function focused on app-level wiring only. Put business logic in
    services and HTTP handlers in route modules.
    """
    configure_logging()

    app = FastAPI(title="AI Traffic Light PC Studio Backend", version=APP_VERSION)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router, tags=["health"])
    app.include_router(smoke_router, prefix="/api/smoke", tags=["smoke"])
    app.include_router(mock_router, prefix="/api/mock", tags=["mock"])
    app.include_router(camera_router, prefix="/api/camera", tags=["camera"])
    app.include_router(inference_router, prefix="/api/inference", tags=["inference"])
    app.include_router(zones_router, prefix="/api/zones", tags=["zones"])
    app.include_router(traffic_router, prefix="/api/traffic", tags=["traffic"])
    app.include_router(dataset_router, prefix="/api/dataset", tags=["dataset"])
    app.include_router(training_router, prefix="/api/training", tags=["training"])
    app.include_router(models_router, prefix="/api/models", tags=["models"])
    app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
    app.include_router(logs_router, prefix="/api/logs", tags=["logs"])
    app.include_router(template_router, prefix="/api/template", tags=["template"])

    logger.info("PC Studio backend app created", extra={"version": APP_VERSION})
    return app


app = create_app()
