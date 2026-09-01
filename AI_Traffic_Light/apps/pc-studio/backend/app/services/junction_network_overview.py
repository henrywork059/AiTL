from __future__ import annotations

from collections.abc import Callable
import time
from typing import Any

from app.services.camera_frames import camera_frame_service
from app.services.decision_context import build_decision_context
from app.services.intersection_network import IntersectionNetworkService, intersection_network_service
from app.services.remote_camera_manager import RemoteCameraManager, remote_camera_manager
from app.services.traffic_logic import get_live_traffic_state

TrafficStateProvider = Callable[[], dict[str, Any]]
FrameProvider = Callable[[], Any | None]
SimulationProvider = Callable[[], bool]


class JunctionNetworkOverviewService:
    """Project junction topology plus honest live observability for the UI.

    The shared CameraFrameService has one selected physical/simulation source,
    so only that resolved junction receives live occupancy/decision data. Every
    configured junction can still expose assigned-camera health, topology,
    warnings and layout metadata without misrepresenting unavailable AI data.
    """

    def __init__(
        self,
        *,
        network_service: IntersectionNetworkService = intersection_network_service,
        camera_manager: RemoteCameraManager = remote_camera_manager,
        traffic_state_provider: TrafficStateProvider = get_live_traffic_state,
        frame_provider: FrameProvider = camera_frame_service.latest_frame,
        simulation_provider: SimulationProvider = lambda: camera_frame_service.simulation_enabled,
    ) -> None:
        self._network_service = network_service
        self._camera_manager = camera_manager
        self._traffic_state_provider = traffic_state_provider
        self._frame_provider = frame_provider
        self._simulation_provider = simulation_provider

    @staticmethod
    def _provenance(*, simulation_enabled: bool, state: dict[str, Any]) -> str:
        explicit = state.get("observation_provenance")
        if explicit in {"ai_detection", "simulation", "manual_test", "unavailable"}:
            return str(explicit)
        signal = state.get("signal_policy") if isinstance(state.get("signal_policy"), dict) else {}
        test_inputs = signal.get("test_inputs") if isinstance(signal.get("test_inputs"), dict) else {}
        manual_test_active = bool(
            signal.get("mode") == "test"
            and any(bool(test_inputs.get(key)) for key in ("mobility_assistance", "incident_person_fallen"))
        )
        if simulation_enabled:
            return "simulation"
        if manual_test_active:
            return "manual_test"
        if state.get("source_timestamp_ms") is not None and not str(state.get("data_source", "")).startswith("inference_unavailable"):
            return "ai_detection"
        return "unavailable"

    @staticmethod
    def _load_level(*, total: int, waiting: int = 0, crossing: int = 0, available: bool) -> str:
        if not available:
            return "unavailable"
        score = max(total, waiting * 2 + crossing * 2)
        if score <= 0:
            return "clear"
        if score <= 3:
            return "light"
        if score <= 7:
            return "moderate"
        return "heavy"

    @staticmethod
    def _remote_camera_view(camera: dict[str, Any]) -> dict[str, Any]:
        streaming = bool(camera.get("streaming"))
        stream_connected = bool(camera.get("stream_connected"))
        reachable = bool(camera.get("device_reachable"))
        configured = bool(camera.get("connected"))
        if streaming and stream_connected:
            state = "streaming"
        elif reachable:
            state = "online"
        elif configured:
            state = "configured"
        else:
            state = "offline"
        return {
            "source_id": camera.get("source_id"),
            "kind": "esp32_cam",
            "saved": True,
            "host": camera.get("host"),
            "selected": bool(camera.get("selected")),
            "connected": configured,
            "device_reachable": reachable,
            "streaming": streaming,
            "stream_connected": stream_connected,
            "measured_fps": round(float(camera.get("measured_fps", 0.0) or 0.0), 2),
            "last_success_at_ms": camera.get("last_success_at_ms"),
            "last_error": camera.get("last_error"),
            "state": state,
        }

    @staticmethod
    def _virtual_source_view(source_id: str, *, simulation_enabled: bool) -> dict[str, Any]:
        return {
            "source_id": source_id,
            "kind": "simulation" if source_id == "simulation_camera" else "other_source",
            "saved": source_id == "simulation_camera",
            "host": None,
            "selected": source_id == "simulation_camera" and simulation_enabled,
            "connected": source_id == "simulation_camera" and simulation_enabled,
            "device_reachable": source_id == "simulation_camera" and simulation_enabled,
            "streaming": source_id == "simulation_camera" and simulation_enabled,
            "stream_connected": source_id == "simulation_camera" and simulation_enabled,
            "measured_fps": 0.0,
            "last_success_at_ms": None,
            "last_error": None,
            "state": "simulation" if source_id == "simulation_camera" and simulation_enabled else "configured",
        }

    @staticmethod
    def _event(
        event_type: str,
        label: str,
        *,
        severity: str = "info",
        detail: str | None = None,
        provenance: str | None = None,
    ) -> dict[str, Any]:
        return {
            "type": event_type,
            "label": label,
            "severity": severity,
            "detail": detail,
            "provenance": provenance,
        }

    @classmethod
    def _events(cls, state: dict[str, Any], decision_context: dict[str, Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        provenance = str(decision_context.get("observation_provenance") or "unavailable")
        category = str(decision_context.get("category") or "normal_timing")
        scenario = decision_context.get("scenario") if isinstance(decision_context.get("scenario"), dict) else {}
        scenario_label = str(scenario.get("label") or "").strip()
        requested_service = decision_context.get("requested_service")

        if category == "incident_test_hold":
            events.append(
                cls._event(
                    "incident_test_hold",
                    "Incident test hold",
                    severity="critical",
                    detail="The simulation/test signal policy is holding the junction in its protected incident state.",
                    provenance=provenance,
                )
            )
        if scenario_label:
            events.append(
                cls._event(
                    "ranked_scenario",
                    scenario_label,
                    severity="attention",
                    detail="Highest-ranked eligible traffic scenario currently executing.",
                    provenance=provenance,
                )
            )
        if requested_service == "pedestrian":
            events.append(
                cls._event(
                    "pedestrian_service",
                    "Pedestrian service requested",
                    severity="attention",
                    provenance=provenance,
                )
            )
        elif requested_service == "vehicle":
            events.append(
                cls._event(
                    "vehicle_service",
                    "Vehicle service requested",
                    severity="info",
                    provenance=provenance,
                )
            )
        if bool(decision_context.get("manual_test_input_active")):
            events.append(
                cls._event(
                    "manual_test_input",
                    "Manual safety/test input active",
                    severity="attention",
                    provenance="manual_test",
                )
            )
        if int(state.get("pedestrians_crossing", 0) or 0) > 0:
            events.append(
                cls._event(
                    "pedestrian_crossing",
                    "Pedestrians in crossing",
                    severity="attention",
                    detail=f"{int(state.get('pedestrians_crossing', 0) or 0)} currently observed in configured crossing zones.",
                    provenance=provenance,
                )
            )
        return events

    @staticmethod
    def _warning(code: str, message: str, *, severity: str = "warning", source_id: str | None = None) -> dict[str, Any]:
        return {"code": code, "message": message, "severity": severity, "source_id": source_id}

    def overview(self) -> dict[str, Any]:
        generated_at_ms = int(time.time() * 1000)
        network = self._network_service.get()
        camera_status = self._camera_manager.status(refresh_device=False)
        simulation_enabled = bool(self._simulation_provider())
        frame = self._frame_provider()
        current_source_id = str(getattr(frame, "source_id", "") or "").strip() or None
        resolution = self._network_service.resolve_source(current_source_id)

        live_state = dict(self._traffic_state_provider())
        provenance = self._provenance(simulation_enabled=simulation_enabled, state=live_state)
        live_state["intersection_id"] = resolution["intersection_id"]
        live_state["observation_provenance"] = provenance
        live_state["network_context"] = resolution["network_context"]
        decision_context = build_decision_context(
            live_state,
            network_resolution=resolution,
            simulation_enabled=simulation_enabled,
        )
        live_state["decision_context"] = decision_context

        remote_cameras = {
            str(item.get("source_id")): item
            for item in camera_status.get("cameras", [])
            if isinstance(item, dict) and str(item.get("source_id") or "")
        }
        remote_camera_views = {
            source_id: self._remote_camera_view(camera)
            for source_id, camera in remote_cameras.items()
        }
        available_cameras = [remote_camera_views[source_id] for source_id in sorted(remote_camera_views)]

        observation_intersection_id = str(resolution["intersection_id"])
        observation_available = provenance != "unavailable"
        junctions: list[dict[str, Any]] = []

        for intersection in network["intersections"]:
            intersection_id = str(intersection["id"])
            assigned_sources = [
                remote_camera_views.get(source_id)
                or self._virtual_source_view(source_id, simulation_enabled=simulation_enabled)
                for source_id in intersection.get("source_ids", [])
            ]
            assigned_source_by_id = {str(source["source_id"]): source for source in assigned_sources}

            live_for_junction = intersection_id == observation_intersection_id
            junction_provenance = provenance if live_for_junction else "unavailable"
            available = live_for_junction and observation_available
            vehicle_total = int(live_state.get("vehicles_total", 0) or 0) if live_for_junction else 0
            vehicle_waiting = int(live_state.get("vehicles_waiting", 0) or 0) if live_for_junction else 0
            pedestrian_total = int(live_state.get("pedestrians_total", 0) or 0) if live_for_junction else 0
            pedestrian_waiting = int(live_state.get("pedestrians_waiting", 0) or 0) if live_for_junction else 0
            pedestrian_crossing = int(live_state.get("pedestrians_crossing", 0) or 0) if live_for_junction else 0

            events = self._events(live_state, decision_context) if live_for_junction else []
            warnings: list[dict[str, Any]] = []
            if not intersection.get("source_ids"):
                warnings.append(self._warning("no_source_assigned", "No camera/source is assigned to this junction.", severity="info"))

            for source in assigned_sources:
                if source["kind"] == "other_source" and not source["saved"]:
                    warnings.append(
                        self._warning(
                            "source_profile_missing",
                            f"Assigned source {source['source_id']} is not a saved ESP camera profile.",
                            source_id=str(source["source_id"]),
                        )
                    )

            remote_assigned = [source for source in assigned_sources if source["kind"] == "esp32_cam"]
            if remote_assigned and not any(bool(source["device_reachable"]) for source in remote_assigned):
                warnings.append(self._warning("all_esp_cameras_offline", "All assigned ESP cameras are currently unreachable or not connected."))
            for source in remote_assigned:
                if source.get("last_error"):
                    warnings.append(
                        self._warning(
                            "camera_error",
                            f"{source['source_id']}: {source['last_error']}",
                            source_id=str(source["source_id"]),
                        )
                    )

            primary_source_id = intersection.get("primary_source_id")
            if primary_source_id:
                primary = assigned_source_by_id.get(str(primary_source_id))
                if primary is None:
                    warnings.append(self._warning("primary_source_missing", "The configured primary camera/source is not assigned to this junction."))
                elif primary["kind"] == "esp32_cam" and not primary["device_reachable"]:
                    warnings.append(
                        self._warning(
                            "primary_camera_offline",
                            f"Primary camera {primary_source_id} is currently unreachable or not connected.",
                            source_id=str(primary_source_id),
                        )
                    )

            if live_for_junction and current_source_id and not bool(resolution.get("source_mapping_matched")):
                warnings.append(
                    self._warning(
                        "current_source_unmapped",
                        f"Current source {current_source_id} is falling back to the active junction because it has no explicit junction assignment.",
                        source_id=current_source_id,
                    )
                )
            if live_for_junction and not observation_available:
                warnings.append(
                    self._warning(
                        "traffic_observation_unavailable",
                        "No current AI/simulation traffic observation is available for the shared selected source.",
                        severity="info",
                    )
                )

            junctions.append(
                {
                    "id": intersection_id,
                    "label": intersection["label"],
                    "enabled": bool(intersection.get("enabled", True)),
                    "active_intersection": intersection_id == network["active_intersection_id"],
                    "position": dict(intersection["position"]),
                    "source_ids": list(intersection.get("source_ids", [])),
                    "primary_source_id": primary_source_id,
                    "signal_profile": intersection.get("signal_profile"),
                    "cameras": assigned_sources,
                    "camera_count": len(assigned_sources),
                    "reachable_camera_count": sum(1 for source in assigned_sources if bool(source["device_reachable"])),
                    "streaming_camera_count": sum(1 for source in assigned_sources if bool(source["streaming"] and source["stream_connected"])),
                    "live": {
                        "available": available,
                        "pipeline_source_active": live_for_junction,
                        "source_id": current_source_id if live_for_junction else None,
                        "source_mapping_matched": bool(resolution.get("source_mapping_matched")) if live_for_junction else False,
                        "observation_provenance": junction_provenance,
                        "phase": live_state.get("phase") if live_for_junction else None,
                        "decision": live_state.get("decision") if live_for_junction else None,
                        "decision_reason": live_state.get("decision_reason") if live_for_junction else None,
                        "evaluated_at_ms": live_state.get("evaluated_at_ms") if live_for_junction else None,
                        "source_timestamp_ms": live_state.get("source_timestamp_ms") if live_for_junction else None,
                        "vehicle": {
                            "total": vehicle_total,
                            "waiting": vehicle_waiting,
                            "load": self._load_level(total=vehicle_total, waiting=vehicle_waiting, available=available),
                        },
                        "pedestrian": {
                            "total": pedestrian_total,
                            "waiting": pedestrian_waiting,
                            "crossing": pedestrian_crossing,
                            "load": self._load_level(
                                total=pedestrian_total,
                                waiting=pedestrian_waiting,
                                crossing=pedestrian_crossing,
                                available=available,
                            ),
                        },
                        "decision_context": decision_context if live_for_junction else None,
                    },
                    "events": events,
                    "warnings": warnings,
                    "warning_count": len(warnings),
                    "event_count": len(events),
                }
            )

        warning_junctions = sum(1 for junction in junctions if junction["warning_count"] > 0)
        event_count = sum(int(junction["event_count"]) for junction in junctions)
        heavy_vehicle_junctions = sum(1 for junction in junctions if junction["live"]["vehicle"]["load"] == "heavy")
        heavy_pedestrian_junctions = sum(1 for junction in junctions if junction["live"]["pedestrian"]["load"] == "heavy")
        assigned_remote_ids = {
            source_id
            for intersection in network["intersections"]
            for source_id in intersection.get("source_ids", [])
            if source_id in remote_cameras
        }

        global_warnings: list[dict[str, Any]] = []
        if camera_status.get("registry_warning"):
            global_warnings.append(
                self._warning(
                    "camera_registry_warning",
                    str(camera_status["registry_warning"]),
                    severity="warning",
                )
            )

        return {
            "schema_version": 1,
            "generated_at_ms": generated_at_ms,
            "network": network,
            "available_cameras": available_cameras,
            "active_source_id": camera_status.get("active_source_id"),
            "current_frame_source_id": current_source_id,
            "observation_intersection_id": observation_intersection_id,
            "observation_provenance": provenance,
            "source_mapping_matched": bool(resolution.get("source_mapping_matched")),
            "simulation_enabled": simulation_enabled,
            "junctions": junctions,
            "links": list(network.get("links", [])),
            "warnings": global_warnings,
            "summary": {
                "junction_count": len(junctions),
                "enabled_junction_count": sum(1 for junction in junctions if junction["enabled"]),
                "link_count": len(network.get("links", [])),
                "saved_esp_camera_count": len(available_cameras),
                "assigned_esp_camera_count": len(assigned_remote_ids),
                "reachable_esp_camera_count": sum(1 for camera in available_cameras if camera["device_reachable"]),
                "streaming_esp_camera_count": sum(1 for camera in available_cameras if camera["streaming"] and camera["stream_connected"]),
                "warning_junction_count": warning_junctions,
                "event_count": event_count,
                "heavy_vehicle_junction_count": heavy_vehicle_junctions,
                "heavy_pedestrian_junction_count": heavy_pedestrian_junctions,
            },
            "multi_camera_assignment": True,
            "simultaneous_multi_junction_inference": False,
            "prototype_only": True,
            "scope_note": (
                "Junction topology, camera assignment and observability are implemented. Only the shared selected camera/simulation "
                "source feeds live AI traffic metrics; unselected junctions show topology/camera health without fabricated occupancy."
            ),
        }


junction_network_overview_service = JunctionNetworkOverviewService()
