from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import AppError, app_error_handler, unhandled_exception_handler
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.routes.health import router as health_router
from app.routes.mock import router as mock_router
from app.routes.traffic import router as traffic_router

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the PC Studio backend app.

    Keep this function focused on app-level wiring only. Put business logic in
    services and HTTP handlers in route modules.
    """
    configure_logging()

    app = FastAPI(title="AI Traffic Light PC Studio Backend", version="0_0_3")

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router, tags=["health"])
    app.include_router(mock_router, prefix="/api/mock", tags=["mock"])
    app.include_router(traffic_router, prefix="/api/traffic", tags=["traffic"])

    logger.info("PC Studio backend app created", extra={"version": "0_0_3"})
    return app


app = create_app()
