from fastapi import APIRouter, Query, Request, Response

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.models import SignalRulesConfigRequest, SignalRulesPreviewRequest, SignalTestInputsRequest
from app.services.camera_frames import camera_frame_service
from app.services.object_tracking import object_tracking_service
from app.services.signal_rules import signal_rules_service
from app.services.traffic_flow import traffic_flow_service
from app.services.traffic_history import traffic_history_service
from app.services.traffic_logic import get_live_traffic_state
from app.services.zones import zone_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/state")
def traffic_state(request: Request) -> dict:
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
    data = traffic_history_service.query(zones=zone_service.zones(), minutes=minutes, limit=limit, region_id=region_id)
    logger.info(
        "Traffic history returned",
        extra={"request_id": request.state.request_id, "sample_count": len(data.get("points", [])), "minutes": minutes, "region_id": region_id},
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/history/export.csv")
def traffic_history_export(
    request: Request,
    minutes: int = Query(default=15, ge=0, le=360),
    limit: int = Query(default=5000, ge=1, le=50_000),
    region_id: str | None = Query(default=None, min_length=1, max_length=64),
) -> Response:
    csv_text = traffic_history_service.export_csv(zones=zone_service.zones(), minutes=minutes, limit=limit, region_id=region_id)
    logger.info("Traffic history CSV exported", extra={"request_id": request.state.request_id, "minutes": minutes, "region_id": region_id})
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="aitl_traffic_history.csv"', "X-Request-ID": request.state.request_id},
    )


@router.delete("/history")
def clear_traffic_history(request: Request) -> dict:
    data = traffic_history_service.clear()
    logger.info("Traffic history cleared through API", extra={"request_id": request.state.request_id, "removed_samples": data.get("removed_samples")})
    return ok(data, request_id=request.state.request_id)


@router.get("/tracks")
def tracking_status(request: Request) -> dict:
    data = object_tracking_service.status()
    logger.info("Traffic tracking status returned", extra={"request_id": request.state.request_id, "active_track_count": data.get("active_track_count")})
    return ok(data, request_id=request.state.request_id)


@router.get("/flow")
def traffic_flow(
    request: Request,
    minutes: int = Query(default=15, ge=0, le=360),
    limit: int = Query(default=10000, ge=1, le=50000),
    line_id: str | None = Query(default=None, min_length=1, max_length=64),
    region_id: str | None = Query(default=None, min_length=1, max_length=64),
    class_name: str | None = Query(default=None, min_length=1, max_length=64),
) -> dict:
    data = traffic_flow_service.query(
        zones=zone_service.zones(),
        minutes=minutes,
        limit=limit,
        line_id=line_id,
        region_id=region_id,
        class_name=class_name,
    )
    logger.info(
        "Traffic flow analytics returned",
        extra={
            "request_id": request.state.request_id,
            "event_count": len(data.get("events", [])),
            "minutes": minutes,
            "line_id": line_id,
            "region_id": region_id,
            "class_name": class_name,
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/flow/export.csv")
def traffic_flow_export(
    request: Request,
    minutes: int = Query(default=15, ge=0, le=360),
    limit: int = Query(default=50000, ge=1, le=100000),
    line_id: str | None = Query(default=None, min_length=1, max_length=64),
    region_id: str | None = Query(default=None, min_length=1, max_length=64),
    class_name: str | None = Query(default=None, min_length=1, max_length=64),
) -> Response:
    csv_text = traffic_flow_service.export_csv(
        zones=zone_service.zones(),
        minutes=minutes,
        limit=limit,
        line_id=line_id,
        region_id=region_id,
        class_name=class_name,
    )
    logger.info("Traffic flow CSV exported", extra={"request_id": request.state.request_id, "minutes": minutes, "line_id": line_id, "region_id": region_id})
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="aitl_traffic_flow.csv"', "X-Request-ID": request.state.request_id},
    )


@router.delete("/flow")
def clear_traffic_flow(request: Request) -> dict:
    data = traffic_flow_service.clear()
    logger.info("Traffic flow history cleared through API", extra={"request_id": request.state.request_id, "removed_events": data.get("removed_events")})
    return ok(data, request_id=request.state.request_id)


@router.get("/signal-rules")
def signal_rules(request: Request) -> dict:
    return ok(signal_rules_service.get_config(), request_id=request.state.request_id)


@router.put("/signal-rules")
def save_signal_rules(payload: SignalRulesConfigRequest, request: Request) -> dict:
    data = signal_rules_service.save_config(payload.config)
    logger.info("Signal rules saved", extra={"request_id": request.state.request_id, "active_profile": data.get("active_profile"), "mode": data.get("mode")})
    return ok(data, request_id=request.state.request_id)


@router.post("/signal-rules/reset")
def reset_signal_rules(request: Request) -> dict:
    data = signal_rules_service.reset_config()
    logger.info("Signal rules reset to defaults", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/signal-rules/runtime/reset")
def reset_signal_rules_runtime(request: Request) -> dict:
    data = camera_frame_service.reset_simulation_signal_policy() if camera_frame_service.simulation_enabled else signal_rules_service.reset_runtime(0.0)
    logger.info("Signal-rule runtime state reset", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/signal-rules/test-inputs")
def set_signal_test_inputs(payload: SignalTestInputsRequest, request: Request) -> dict:
    data = signal_rules_service.set_test_inputs(payload.model_dump())
    logger.info("Signal-rule test inputs updated", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/signal-rules/incident/clear")
def clear_signal_incident(request: Request) -> dict:
    data = signal_rules_service.clear_incident()
    logger.info("Signal-rule incident hold cleared", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/signal-rules/preview")
def preview_signal_rules(payload: SignalRulesPreviewRequest, request: Request) -> dict:
    data = signal_rules_service.preview(payload.model_dump())
    return ok(data, request_id=request.state.request_id)


@router.get("/signal-status")
def signal_status(request: Request) -> dict:
    if camera_frame_service.simulation_enabled:
        data = camera_frame_service.simulation_signal_state()
    else:
        data = signal_rules_service.status(0.0)
        data["fallback_reason"] = "Simulation mode is not running; status is a policy preview only."
    return ok(data, request_id=request.state.request_id)


@router.get("/signal-rules/history")
def signal_rules_history(request: Request, limit: int = Query(default=200, ge=1, le=2000)) -> dict:
    return ok(signal_rules_service.history(limit), request_id=request.state.request_id)


@router.delete("/signal-rules/history")
def clear_signal_rules_history(request: Request) -> dict:
    return ok(signal_rules_service.clear_history(), request_id=request.state.request_id)
