from fastapi import APIRouter, Query, Request, Response

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.models import IntersectionNetworkConfigRequest, SignalRulesConfigRequest, SignalRulesPreviewRequest, SignalTestInputsRequest
from app.services.camera_frames import camera_frame_service
from app.services.decision_context import build_decision_context
from app.services.intersection_network import intersection_network_service
from app.services.object_tracking import object_tracking_service
from app.services.signal_rules import signal_rules_service
from app.services.traffic_flow import traffic_flow_service
from app.services.traffic_history import traffic_history_service
from app.services.traffic_logic import get_live_traffic_state
from app.services.zones import zone_service

router = APIRouter()
logger = get_logger(__name__)


def _enrich_network_context(state: dict) -> dict:
    frame = camera_frame_service.latest_frame()
    source_id = frame.source_id if frame is not None else None
    resolution = intersection_network_service.resolve_source(source_id)
    enriched = dict(state)
    signal = enriched.get("signal_policy") if isinstance(enriched.get("signal_policy"), dict) else {}
    manual_test_active = bool(
        signal.get("mode") == "test"
        and isinstance(signal.get("test_inputs"), dict)
        and any(
            bool(signal["test_inputs"].get(key))
            for key in ("mobility_assistance", "incident_person_fallen")
        )
    )
    if camera_frame_service.simulation_enabled:
        provenance = "simulation"
    elif manual_test_active:
        provenance = "manual_test"
    elif enriched.get("source_timestamp_ms") is not None and not str(enriched.get("data_source", "")).startswith("inference_unavailable"):
        provenance = "ai_detection"
    else:
        provenance = "unavailable"
    enriched["intersection_id"] = resolution["intersection_id"]
    enriched["observation_provenance"] = provenance
    enriched["network_context"] = resolution["network_context"]
    enriched["decision_context"] = build_decision_context(
        enriched,
        network_resolution=resolution,
        simulation_enabled=camera_frame_service.simulation_enabled,
    )
    return enriched


@router.get("/state")
def traffic_state(request: Request) -> dict:
    state = _enrich_network_context(get_live_traffic_state())
    traffic_history_service.record_state(state)
    logger.info(
        "Traffic simulation state returned",
        extra={
            "request_id": request.state.request_id,
            "intersection_id": state.get("intersection_id"),
            "phase": state.get("phase"),
            "decision": state.get("decision"),
            "frame_number": state.get("evaluated_frame_number"),
            "pedestrians": state.get("pedestrians_total"),
            "vehicles": state.get("vehicles_total"),
        },
    )
    return ok(state, request_id=request.state.request_id)


@router.get("/network")
def intersection_network(request: Request) -> dict:
    data = intersection_network_service.get()
    return ok(
        {
            **data,
            "config_path": intersection_network_service.relative_config_path(),
            "cooperative_control_active": False,
            "prototype_only": True,
        },
        request_id=request.state.request_id,
    )


@router.put("/network")
def save_intersection_network(payload: IntersectionNetworkConfigRequest, request: Request) -> dict:
    data = intersection_network_service.save(payload.config)
    logger.info(
        "Intersection network configuration saved",
        extra={
            "request_id": request.state.request_id,
            "active_intersection_id": data.get("active_intersection_id"),
            "intersection_count": len(data.get("intersections", [])),
            "link_count": len(data.get("links", [])),
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/network/reset")
def reset_intersection_network(request: Request) -> dict:
    data = intersection_network_service.reset()
    logger.info("Intersection network configuration reset", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/network/context")
def intersection_network_context(
    request: Request,
    intersection_id: str | None = Query(default=None, min_length=1, max_length=64),
) -> dict:
    return ok(intersection_network_service.context(intersection_id), request_id=request.state.request_id)


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
