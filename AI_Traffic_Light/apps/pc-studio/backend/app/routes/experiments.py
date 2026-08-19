from fastapi import APIRouter, Query, Request, Response

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.models import SimulationExperimentRunRequest
from app.services.simulation_experiments import simulation_experiment_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/experiments")
def run_simulation_experiment(payload: SimulationExperimentRunRequest, request: Request) -> dict:
    data = simulation_experiment_service.run(**payload.model_dump())
    logger.info(
        "Fixed-vs-adaptive simulation experiment completed",
        extra={
            "request_id": request.state.request_id,
            "run_id": data.get("run_id"),
            "duration_seconds": payload.duration_seconds,
            "density": payload.density,
            "profile": data.get("scenario", {}).get("profile"),
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/experiments")
def list_simulation_experiments(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> dict:
    data = simulation_experiment_service.list(limit)
    return ok(data, request_id=request.state.request_id)


@router.get("/experiments/{run_id}/export.csv")
def export_simulation_experiment(run_id: str, request: Request) -> Response:
    csv_text = simulation_experiment_service.export_csv(run_id)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="aitl_{run_id}.csv"',
            "X-Request-ID": request.state.request_id,
        },
    )


@router.get("/experiments/{run_id}")
def get_simulation_experiment(run_id: str, request: Request) -> dict:
    return ok(simulation_experiment_service.get(run_id), request_id=request.state.request_id)


@router.delete("/experiments/{run_id}")
def delete_simulation_experiment(run_id: str, request: Request) -> dict:
    data = simulation_experiment_service.delete(run_id)
    logger.info(
        "Simulation experiment deleted",
        extra={"request_id": request.state.request_id, "run_id": run_id},
    )
    return ok(data, request_id=request.state.request_id)
