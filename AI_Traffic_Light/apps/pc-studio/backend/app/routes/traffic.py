from fastapi import APIRouter, Query, Request, Response

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.traffic_history import traffic_history_service
from app.services.traffic_logic import get_live_traffic_state
from app.services.zones import zone_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/state")
def traffic_state(request: Request) -> dict:
    """Return the current live-detection-based traffic-light simulation recommendation and occupancy counts."""
    state = get_live_traffic_state()
    traffic_history_service.record_state(state)
    logger.info(
        "Traffic simulation state returned",
        extra={
            "request_id": request.state.request_id,
            "phase": state.get("phase"),
            "decision": state.get("decision"),
            "frame_number": state.get("evaluated_frame_number"),
            "pedestrians": state.get("pedestrians_total"),
            "vehicles": state.get("vehicles_total"),
        },
    )
    return ok(state, request_id=request.state.request_id)


@router.get("/history")
def traffic_history(
    request: Request,
    minutes: int = Query(default=15, ge=0, le=360),
    limit: int = Query(default=2000, ge=1, le=10_000),
    region_id: str | None = Query(default=None, min_length=1, max_length=64),
) -> dict:
    """Return sampled vehicle/pedestrian occupancy history for the whole frame or one configured region."""
    data = traffic_history_service.query(
        zones=zone_service.zones(),
        minutes=minutes,
        limit=limit,
        region_id=region_id,
    )
    logger.info(
        "Traffic history returned",
        extra={
            "request_id": request.state.request_id,
            "sample_count": len(data.get("points", [])),
            "minutes": minutes,
            "region_id": region_id,
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/history/export.csv")
def traffic_history_export(
    request: Request,
    minutes: int = Query(default=15, ge=0, le=360),
    limit: int = Query(default=5000, ge=1, le=50_000),
    region_id: str | None = Query(default=None, min_length=1, max_length=64),
) -> Response:
    """Export the selected occupancy-history scope as CSV for local analysis."""
    csv_text = traffic_history_service.export_csv(
        zones=zone_service.zones(),
        minutes=minutes,
        limit=limit,
        region_id=region_id,
    )
    logger.info(
        "Traffic history CSV exported",
        extra={"request_id": request.state.request_id, "minutes": minutes, "region_id": region_id},
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="aitl_traffic_history.csv"',
            "X-Request-ID": request.state.request_id,
        },
    )


@router.delete("/history")
def clear_traffic_history(request: Request) -> dict:
    """Clear persisted traffic-history runtime data after explicit user confirmation in the frontend."""
    data = traffic_history_service.clear()
    logger.info(
        "Traffic history cleared through API",
        extra={"request_id": request.state.request_id, "removed_samples": data.get("removed_samples")},
    )
    return ok(data, request_id=request.state.request_id)
