"""Manually stepped native-only evaluation; never a selected camera or physical controller."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
import json
import logging
import math
import hashlib
import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, RLock, Timer
import time
from uuid import uuid4
from zipfile import ZipFile

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.dataset_capture import DatasetCaptureService
from app.services.simulation_experiments import _BenchmarkSignalRulesService
from app.services.signal_rules import signal_rules_service
from app.services.experiment_timeline_csv import serialize_experiment_timeline
from app.services.simulation_finite_fixture import load_trips, RouteGateAdapter
from app.services.simulation_gate_metrics import GateMetrics, STEP_S
from app.services.sumo_frame_publisher import NativeFramePublisher
from app.services.sumo_projection import NativeProjection, Projection, PROVENANCE, VIEW_FLIPS, export_csv
from app.services.sumo_shadow_adapter import SumoShadowAdapter
from app.services.sumo_shadow_fixture import DENSITY_COUNTS, GEOMETRY_PRESETS, PHASES, PhaseMap
from app.services.sumo_shadow_runtime import GeneratedSession
from app.services.native_evaluation_geometry import region_counts, legacy_rectangle_preview, footprint_center_counts
from app.services.camera_frames import LEGACY_LAYOUT_ID
from app.services.legacy_world import ROAD_TOP, ROAD_BOTTOM, CROSSING_LEFT, CROSSING_RIGHT
from app.services.native_detector_validation import footprint_annotations
from app.services.native_evaluation_experiments import summarize_timeline, validate_pair, vehicle_braking_sample, summarize_braking, vehicle_centerline_events
from app.services.simulation_gate_reporting import normalized_report_metrics
from app.services.simulation_wait_metrics import NativeApproachWait
from app.services.observation_identity import (synthetic_scene_identity, evaluation_source_id,
    REFERENCE_EVALUATION_ORIGIN, simulation_view_point)
from app.services.simulation_reference_session import GeneratedReferenceSession
from app.services.sumo_midblock_session import CyclicMidblockSession
from app.services.sumo_midblock_fixture import LENGTHS, WIDTHS, MIDBLOCK_GEOMETRIES


def valid_geometry(engine,geometry):
    return geometry in GEOMETRY_PRESETS or (engine=="native" and geometry in MIDBLOCK_GEOMETRIES)

ENGINES = {"native": PROVENANCE, "reference": REFERENCE_EVALUATION_ORIGIN}

MAX_TICKS = 2500
MAX_BATCH = 25
logger = logging.getLogger(__name__)


class NativeEvaluationService:
    def __init__(self, *, enabled=False, factory=GeneratedSession, trip_loader=load_trips, phase_loader=PhaseMap.load,
                 reference_factory=GeneratedReferenceSession,midblock_factory=CyclicMidblockSession,indexed_frames=True,camera_lease_seconds=30.):
        self.enabled = enabled
        self._factory, self._trip_loader, self._phase_loader = factory, trip_loader, phase_loader
        self._reference_factory = reference_factory
        self._midblock_factory = midblock_factory
        self._indexed_frames = indexed_frames
        if not 0<camera_lease_seconds<=120:
            raise ValueError("Invalid camera lease interval")
        self._camera_lease_seconds=camera_lease_seconds
        self._camera_owner=None
        self._camera_deadline=0.
        self._camera_timer=None
        self._lock = RLock()
        self._comparison = None
        self.epoch = uuid4().hex
        self.generation = 0
        self._state = "idle" if enabled else "disabled"
        self._publisher = NativeFramePublisher()
        self._adapter = self._session = self._controller = self._projection = None
        self._temp = self._metrics = self._routes = self._phase_map = None
        self._timeline = []
        self._signal = self._received_at_ms = self._density = self._mode = None
        self._paused = False
        self._policy = None
        self._demand_digest = None
        self._demand_manifest = None
        self._geometry = None
        self._engine = None
        self._trips = ()
        self._seen_trips = set()
        self._centerline_seen = set()
        self._approach_wait = None

    @staticmethod
    def _conflict(message):
        return AppError(ErrorCode.CAMERA_STREAM_NOT_STARTED, message, status_code=409)

    def _require(self, epoch, generation, tick=None, *, running=True):
        if not self.enabled:
            raise self._conflict("Standalone native evaluation is disabled.")
        if self._expire_camera_if_due():
            raise self._conflict("Native camera ownership expired.")
        if epoch != self.epoch or generation != self.generation:
            raise self._conflict("Retired native evaluation generation.")
        if self._comparison is not None:
            raise self._conflict("Native comparison is busy.")
        if running and self._state != "running":
            raise self._conflict("No active native evaluation.")
        if tick is not None and (self._adapter is None or self._adapter.snapshot().tick != tick):
            raise self._conflict("Retired native evaluation tick.")

    def _retire(self, state="idle"):
        if self._camera_timer is not None:
            self._camera_timer.cancel()
        self._camera_timer=None
        self._camera_owner=None
        self._camera_deadline=0.
        self.generation += 1
        self._publisher.invalidate()
        adapter, temp = self._adapter, self._temp
        self._adapter = self._session = self._controller = self._projection = None
        self._temp = self._metrics = self._routes = self._phase_map = None
        self._timeline = []
        self._signal = self._received_at_ms = self._density = self._mode = None
        self._paused = False
        self._policy = None
        self._demand_digest = None
        self._demand_manifest = None
        self._geometry = None
        self._engine = None
        self._trips = ()
        self._seen_trips = set()
        self._centerline_seen = set()
        self._approach_wait = None
        self._state = state
        try:
            if adapter is not None:
                adapter.shutdown()
        finally:
            if temp is not None:
                temp.cleanup()

    def _failure(self):
        try:
            self._retire("unavailable")
        except Exception:
            pass
        return AppError(ErrorCode.CAMERA_FRAME_READ_FAILED, "Native evaluation failed and was retired.", status_code=503)

    def _require_camera_owner(self, token):
        if self._camera_owner is not None and token!=self._camera_owner:
            raise self._conflict("Native camera workspace owns this session.")
        if token is not None and (not isinstance(token,str) or not re.fullmatch(r"[0-9a-f]{32}",token)):
            raise AppError(ErrorCode.INVALID_REQUEST,"Invalid camera owner token.",status_code=422)

    def _arm_camera_timer(self, generation, delay):
        timer=Timer(delay,self._expire_camera,args=(generation,))
        timer.daemon=True
        self._camera_timer=timer
        timer.start()

    def _expire_camera(self,generation):
        with self._lock:
            if self.generation!=generation or self._camera_owner is None:
                return
            remaining=self._camera_deadline-time.monotonic()
            if remaining>0:
                self._arm_camera_timer(generation,remaining)
                return
            self._expire_camera_if_due()

    def _expire_camera_if_due(self):
        """Under the owner lock, expire even when the watchdog is delayed."""
        if self._camera_owner is None or time.monotonic()<self._camera_deadline:
            return False
        try:
            self._retire()
        except Exception:
            logger.exception("Native camera lease retirement failed")
            self._state="unavailable"
        return True

    def _renew_camera(self):
        if self._camera_owner is not None:
            self._camera_deadline=time.monotonic()+self._camera_lease_seconds

    def camera_heartbeat(self,*,epoch,generation,camera_owner):
        with self._lock:
            self._require(epoch,generation)
            self._require_camera_owner(camera_owner)
            if self._camera_owner is None:
                raise self._conflict("No native camera ownership.")
            self._renew_camera()
            return {"epoch":self.epoch,"generation":self.generation,"camera_owned":True}

    def release_camera(self,*,epoch,camera_owner,generation=None):
        with self._lock:
            self._expire_camera_if_due()
            # A delayed keepalive from a previous reset must not close a new
            # session, even if the same workspace owns both generations.
            if epoch!=self.epoch or generation!=self.generation or self._camera_owner is None:
                return {"released":False}
            self._require_camera_owner(camera_owner)
            self._retire()
            return {"released":True}

    def start(self, *, epoch, generation, density, seed, mode, policy_config=None, profile=None, geometry='standard', engine='native',camera_owner=None):
        with self._lock:
            self._require(epoch, generation, running=False)
            self._require_camera_owner(camera_owner)
            if camera_owner is not None and self._state=="running" and self._camera_owner is None:
                raise self._conflict("Stop standalone evaluation before claiming native camera workspace.")
            if engine not in ENGINES or not valid_geometry(engine,geometry) or density not in DENSITY_COUNTS or mode not in ("fixed", "adaptive") or type(seed) is not int or not 0 <= seed <= 2**31-1:
                raise AppError(ErrorCode.INVALID_REQUEST, "Invalid native evaluation settings.", status_code=422)
            try:
                self._retire()
                self._temp = TemporaryDirectory(prefix="mesh-native-evaluation-")
                folder = Path(self._temp.name)
                self._controller = _BenchmarkSignalRulesService(config_path=folder/"signals.json",
                    history_path=folder/"history.jsonl", respect_environment=False)
                config = deepcopy(policy_config) if policy_config is not None else self._controller.defaults()
                if profile is not None:
                    config["active_profile"] = profile
                config["mode"] = mode
                config["dry_run"] = False
                self._policy = self._controller.save_config(config)
                self._controller.reset_runtime(0.)
                self._engine = engine
                cyclic = geometry in MIDBLOCK_GEOMETRIES
                factory = self._midblock_factory if cyclic else (self._factory if engine=="native" else self._reference_factory)
                def open_session(value):
                    kwargs = {'density': density}
                    if geometry not in ('standard','midblock'):
                        kwargs['geometry'] = geometry
                    self._session = factory(value, **kwargs)
                    return self._session
                self._adapter = SumoShadowAdapter(open_session)
                self._adapter.reset(seed=seed)
                network = self._session.network_path
                profiles=None
                if cyclic:
                    profiles={slot.ident:{"kind":slot.kind,**({"vehicle_type":slot.type_id,
                        "length_m":LENGTHS[slot.type_id],"width_m":WIDTHS[slot.type_id],
                        "eastbound":slot.route==("WC","CE")} if slot.kind=="vehicle" else {})}
                        for slot in self._session.ledger.slots.values()}
                self._projection = NativeProjection(Projection.load(network,walking_area_polygons=cyclic), self.generation, provenance=ENGINES[engine],slot_profiles=profiles)
                trips = (self._session.trips if engine=="reference" or cyclic else
                         self._trip_loader(network, network.parent/"routes.xml"))
                self._trips = tuple(trips)
                self._routes = RouteGateAdapter(trips)
                self._demand_manifest = self._session.demand_manifest if cyclic else [asdict(t) for t in trips]
                self._demand_digest = hashlib.sha256(json.dumps(self._demand_manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()
                self._phase_map = self._session.phase_map if engine=="reference" or cyclic else self._phase_loader(network)
                self._metrics = GateMetrics()
                self._approach_wait = NativeApproachWait() if cyclic else None
                self._publisher.begin(self.generation,provenance=ENGINES[engine])
                self._received_at_ms = time.time_ns() // 1_000_000
                self._density, self._mode = density, mode
                self._geometry = geometry
                self._state = "running"
                if camera_owner is not None:
                    self._camera_owner=camera_owner
                    self._renew_camera()
                    self._arm_camera_timer(self.generation,self._camera_lease_seconds)
                return self.scene()
            except Exception as exc:
                logger.exception("Isolated native evaluation operation failed; retiring session")
                raise self._failure() from exc

    def step(self, *, epoch, generation, tick, steps, _return_scene=True,camera_owner=None):
        with self._lock:
            self._require(epoch, generation, tick)
            self._require_camera_owner(camera_owner)
            if camera_owner is not None and self._camera_owner is None:
                raise self._conflict("No native camera ownership.")
            if self._paused or tick >= MAX_TICKS:
                raise self._conflict("Native evaluation paused or at its horizon.")
            if type(steps) is not int or not 1 <= steps <= MAX_BATCH or tick + steps > MAX_TICKS:
                raise AppError(ErrorCode.INVALID_REQUEST, "Step batch exceeds native evaluation bounds.", status_code=422)
            try:
                for _ in range(steps):
                    before = self._adapter.snapshot()
                    prior = self._timeline[-1] if self._timeline else {}
                    crossing = sum(x.kind=="pedestrian" and x.road_id in self._phase_map.crossing_edges for x in before.agents)
                    self._controller.set_benchmark_clock(before.time_s)
                    self._controller.observe({"vehicles_waiting":prior.get("vehicle_queue",0),
                        "pedestrians_waiting":prior.get("pedestrian_queue",0),"pedestrians_crossing":crossing,
                        "source_frame_number":before.tick,"data_source":"synthetic_native_evaluation"})
                    signal = self._controller.signal_state(before.time_s)
                    phase = signal["phase"]
                    if phase not in PHASES or (signal["vehicle_go"] and signal["pedestrian_walk"]):
                        raise RuntimeError("Conflicting or unknown protected phase")
                    self._session.set_phase(phase)
                    snap = self._adapter.step()
                    self._seen_trips.update(a.engine_id for a in snap.agents)
                    permission = self._session.last_permission
                    vehicle_inside=any(a.kind=="vehicle" and a.road_id.startswith(":C_") for a in before.agents)
                    pedestrian_inside=bool(crossing)
                    if self._geometry in MIDBLOCK_GEOMETRIES:
                        vehicle_inside,pedestrian_inside=self._session.occupied(before.agents)
                        self._session.occupied(snap.agents)
                        trips=self._session.trips
                        if len(trips)!=len(self._trips):
                            self._trips=trips
                            self._routes.trips.update({t.ident:t for t in trips})
                    expected=self._phase_map.state(phase,vehicle_inside=vehicle_inside,pedestrian_inside=pedestrian_inside)
                    if permission!=expected:
                        raise RuntimeError("Native permission differs from protected phase map")
                    grants = {i for i,c in enumerate(permission) if c=="G"}
                    if (grants.intersection(self._phase_map.vehicles) and grants.intersection(self._phase_map.pedestrians) or
                        grants and phase not in ("vehicle_green","pedestrian_green") or
                        grants.intersection(self._phase_map.vehicles) and (crossing or phase!="vehicle_green") or
                        grants.intersection(self._phase_map.pedestrians) and phase!="pedestrian_green"):
                        raise RuntimeError("Invalid native permission")
                    rows=self._routes.observations(snap.agents)
                    measured = self._metrics.sample(snap.tick,rows)
                    if self._approach_wait is not None:
                        measured.update(self._approach_wait.sample(snap.tick,before.agents,snap.agents,rows,self._routes.trips))
                    if self._geometry in MIDBLOCK_GEOMETRIES and self._routes.unknown_roads:
                        raise RuntimeError("Cyclic agent left its validated route")
                    braking=vehicle_braking_sample(before.agents,snap.agents) if self._geometry in MIDBLOCK_GEOMETRIES else {}
                    centerline={}
                    if self._geometry in MIDBLOCK_GEOMETRIES:
                        events=vehicle_centerline_events(before.agents,snap.agents,self._session.ledger.slots,
                            self._session.bounds,self._centerline_seen)
                        self._centerline_seen.update(events)
                        centerline={"vehicle_centerline_event_ids":events,
                                    "vehicle_centerline_passages":len(self._centerline_seen)}
                    self._timeline.append({**measured,**braking,**centerline,"phase":phase,"t":measured["t_seconds"],
                        "active_rules":list(signal.get("active_rules",[])),"applied_permission":permission,
                        "vehicle_trip_arrivals":len(self._session.arrived),"pedestrian_trip_arrivals":len(self._session.person_arrived)})
                    self._signal = {"phase":phase,"vehicle_go":signal["vehicle_go"],
                        "pedestrian_walk":signal["pedestrian_walk"],"seconds_remaining":signal["seconds_remaining"],
                        "applied_permission":permission,
                        "applied_vehicle_go":bool(grants.intersection(self._phase_map.vehicles)),
                        "applied_pedestrian_walk":bool(grants.intersection(self._phase_map.pedestrians))}
                self._publisher.retire_before(snap.tick)
                self._received_at_ms = time.time_ns() // 1_000_000
                self._renew_camera()
                return self.scene() if _return_scene else None
            except Exception as exc:
                logger.exception("Isolated native evaluation operation failed; retiring session")
                raise self._failure() from exc

    def pause(self, *, epoch, generation, tick, paused,camera_owner=None):
        with self._lock:
            self._require(epoch,generation,tick)
            self._require_camera_owner(camera_owner)
            if camera_owner is not None and self._camera_owner is None:
                raise self._conflict("No native camera ownership.")
            if type(paused) is not bool:
                raise AppError(ErrorCode.INVALID_REQUEST, "Pause must be boolean.", status_code=422)
            self._paused = paused
            self._renew_camera()
            return self.scene()

    def stop(self, *, epoch, generation,camera_owner=None):
        with self._lock:
            self._require(epoch,generation,running=False)
            self._require_camera_owner(camera_owner)
            if camera_owner is not None and self._camera_owner is None:
                raise self._conflict("No native camera ownership.")
            self._retire()
            return self.scene()

    def close(self):
        with self._lock:
            comparison = self._comparison
            if comparison is not None:
                comparison[0].set()
            self._retire("idle" if self.enabled else "disabled")
        if comparison is not None:
            # Wait at most for the current serialized child operation; the
            # comparison checks cancellation before starting another batch.
            comparison[1].close()

    def scene(self, *, source_id="simulation_camera", _include_lanes=True):
        with self._lock:
            self._expire_camera_if_due()
            snapshot = None
            if self._state == "running":
                snap = self._adapter.snapshot()
                snapshot = {**self._projection.scene(snap, source_id,include_lanes=_include_lanes),"received_at_ms":self._received_at_ms,
                    "paused":self._paused,"density":self._density,"geometry":self._geometry,"engine":self._engine,"signal":deepcopy(self._signal),
                    "epoch":self.epoch,"profile":self._policy["active_profile"],
                    "legacy_editor_compatible":False}
                if self._geometry in MIDBLOCK_GEOMETRIES:
                    snapshot["legacy_preview_layout_id"]=LEGACY_LAYOUT_ID
                    snapshot["legacy_preview_crossing"]=[[CROSSING_LEFT,ROAD_TOP],[CROSSING_RIGHT,ROAD_TOP],
                        [CROSSING_RIGHT,ROAD_BOTTOM],[CROSSING_LEFT,ROAD_BOTTOM]]
                    snapshot["demand_model"]="native_cyclic_slots_v1"
                    snapshot["demand_digest"]=self._demand_digest
                    # Slot and vehicle geometry metadata is owned by the shared projection.
            return {"status":self._state,"provenance":ENGINES.get(self._engine,PROVENANCE),"epoch":self.epoch,
                "generation":self.generation,"snapshot":snapshot,"mode":self._mode,
                "density":self._density,"geometry":self._geometry,"max_ticks":MAX_TICKS,"native_only":self._engine!="reference","engine":self._engine,
                "evaluation_only":True,"camera_owned":self._camera_owner is not None,"available_engines":list(ENGINES) if self.enabled else [],
                "profile":self._policy["active_profile"] if self._policy else None,"physical_output_allowed":False}

    def _ensure_frames(self):
        snap = self._adapter.snapshot()
        if not self._publisher.has_tick(snap.tick):
            indexed=self._geometry in MIDBLOCK_GEOMETRIES and self._indexed_frames
            meta, pixels = self._projection.render_pixels(snap,indexed=indexed)
            meta.update(epoch=self.epoch)
            if self._geometry in MIDBLOCK_GEOMETRIES:
                meta.update(demand_model="native_cyclic_slots_v1",demand_digest=self._demand_digest)
            self._publisher.prepare(meta,pixels,received_at_ms=self._received_at_ms,transfer_owned=True,indexed=indexed)

    def frame(self, *, epoch, generation, tick, source_id):
        with self._lock:
            self._require(epoch,generation,tick)
            if source_id not in VIEW_FLIPS:
                raise AppError(ErrorCode.CAMERA_SOURCE_INVALID, "Unknown native evaluation view.", status_code=422)
            try:
                return self._qualified_frame(tick,source_id)
            except Exception as exc:
                logger.exception("Isolated native evaluation operation failed; retiring session")
                raise self._failure() from exc

    def _qualified_frame(self,tick,source_id):
        """Validate every binary or capture publication against its owner."""
        self._ensure_frames()
        frame=self._publisher.frame_for(source_id)
        origin=ENGINES[self._engine]
        if (frame is None or frame.observation_epoch!=self.epoch or
            frame.mode_generation!=self.generation or frame.frame_number!=tick or
            frame.layout_id!=self._projection.layout_id or frame.coordinate_space!="native_projection_v1" or
            frame.source_id!=evaluation_source_id(origin,self.generation,source_id) or
            frame.origin!=origin or not frame.evaluation_only or
            (frame.width,frame.height)!=(1280,720) or frame.content_type!="image/png" or
            frame.received_at_ms!=self._received_at_ms or
            (self._geometry in MIDBLOCK_GEOMETRIES and frame.simulation_demand_digest!=self._demand_digest)):
            raise ValueError("Native frame identity mismatch")
        return frame

    def exact_simulation_frame(self, *, epoch, generation, tick, layout_id, source_id, engine="native"):
        """Same read seam as the legacy frame owner; no authority transfer."""
        with self._lock:
            self._require(epoch,generation,tick)
            if engine != self._engine or layout_id != self._projection.layout_id:
                raise self._conflict("Evaluation engine or publication layout mismatch.")
            return self.frame(epoch=epoch,generation=generation,tick=tick,source_id=source_id)

    def current_simulation_scene(self, source_id, *, engine="native"):
        with self._lock:
            self._require(self.epoch,self.generation)
            if engine != self._engine:
                raise self._conflict("Evaluation engine mismatch.")
            return self.view_scene(epoch=self.epoch,generation=self.generation,
                                   tick=self._adapter.snapshot().tick,source_id=source_id)

    def capture(self, *, epoch, generation, tick):
        """Bounded four-view ZIP; never writes user datasets."""
        with self._lock:
            self._require(epoch,generation,tick)
            try:
                self._ensure_frames()
                with TemporaryDirectory(prefix="mesh-native-capture-") as tmp:
                    writer=DatasetCaptureService(dataset_root=Path(tmp),respect_environment=False)
                    stream=BytesIO()
                    with ZipFile(stream,"w") as z:
                        image_hashes={}
                        for sid in VIEW_FLIPS:
                            frame=self._qualified_frame(tick,sid)
                            image_hashes[sid+".png"]=hashlib.sha256(frame.content).hexdigest()
                            rec=writer.capture_frame(frame,session_id="native_evaluation" if self._engine=="native" else "reference_evaluation")
                            z.writestr(sid+".png",(writer.dataset_root/rec.image_path).read_bytes())
                            z.writestr(sid+".json",(writer.dataset_root/rec.metadata_path).read_bytes())
                        meta=self.scene()["snapshot"]
                        scene_bytes=json.dumps(meta,indent=2).encode("utf-8")
                        z.writestr("scene.json",scene_bytes)
                        z.writestr("capture_integrity.json",json.dumps({"schema_version":1,"sha256":{
                            **image_hashes,"scene.json":hashlib.sha256(scene_bytes).hexdigest()}},indent=2))
                        z.writestr("coordinate_contract.json",json.dumps({"epoch":epoch,"generation":generation,"tick":tick,"layout_id":meta["layout_id"],"engine":self._engine,"provenance":meta["provenance"],"coordinate_space":meta["coordinate_space"],"width":1280,"height":720,"views":list(VIEW_FLIPS),"legacy_editor_compatible":False,**({"demand_model":meta["demand_model"],"demand_digest":meta["demand_digest"]} if self._geometry in MIDBLOCK_GEOMETRIES else {})},indent=2))
                        z.writestr("agents.csv",export_csv(meta))
                        observations=[self.view_scene(epoch=epoch,generation=generation,tick=tick,source_id=sid)["observation"] for sid in VIEW_FLIPS]
                        z.writestr("observations.json",json.dumps(observations,indent=2))
                        z.writestr("synthetic_footprints.json",json.dumps(footprint_annotations(meta),indent=2))
                        z.writestr("detector_contract.json",json.dumps({"schema_version":1,"observation_kind":"synthetic_ground_truth",
                            "detector_input_eligible":False,"detector_observation":False,"authoritative":False,
                            "physical_output_allowed":False,"coordinate_space":meta["coordinate_space"],"layout_id":meta["layout_id"],
                            "observations":observations,"limitations":"Synthetic rendered scene; no model inference, detector calibration or production signal authority."},indent=2))
                    return stream.getvalue()
            except Exception as exc:
                logger.exception("Isolated native evaluation operation failed; retiring session")
                raise self._failure() from exc

    def _trip_accounting(self):
        snap = self._adapter.snapshot()
        active = {a.engine_id for a in snap.agents}
        arrived = set(self._session.arrived) | set(self._session.person_arrived)
        offered = {t.ident for t in self._trips}
        if not active.isdisjoint(arrived) or not (active | arrived) <= offered:
            raise RuntimeError("Inconsistent native trip identity")
        return {"offered": sorted(offered), "active": sorted(active),
                "arrived": sorted(arrived),
                "not_observed_due": sorted(t.ident for t in self._trips
                    if t.depart_s <= snap.time_s and t.ident not in self._seen_trips | arrived | active),
                "not_yet_due": sorted(t.ident for t in self._trips
                    if t.depart_s > snap.time_s and t.ident not in self._seen_trips | arrived | active),
                "retired_without_arrival": sorted(self._seen_trips - active - arrived)}

    def export(self, *, epoch, generation, tick):
        with self._lock:
            self._require(epoch,generation,tick)
            return {"schema_version":1,"engine":self._engine,"provenance":"synthetic_native_gate_evaluation" if self._engine=="native" else "synthetic_finite_reference_gate_evaluation",
                "metric_contract":"normalized_physical_service_gate_v1","seed":self._adapter.snapshot().seed,
                "mode":self._mode,"density":self._density,"geometry":self._geometry,"step_s":STEP_S,"summary":self._metrics.summary(),
                "timeline":deepcopy(self._timeline),"observed_routes":deepcopy(self._routes.seen_roads),
                "layout_id":self._projection.layout_id,"coordinate_space":"native_projection_v1",
                "policy_config":deepcopy(self._policy),"legacy_editor_compatible":False,
                "demand_digest":self._demand_digest,"derived_metrics":summarize_timeline(self._timeline,self._metrics.summary()),
                "waiting_episodes":self._metrics.waiting_episodes(),
                "normalized_report_metrics":normalized_report_metrics(self._timeline,self._metrics.summary(),self._metrics.waiting_episodes()),
                "demand_manifest":deepcopy(self._demand_manifest),
                **({"demand_model":"native_cyclic_slots_v1","journey_manifest":[asdict(t) for t in self._trips],
                    "slot_visits":dict(self._session.ledger.visits),"current_visits":dict(self._session.ledger.current),
                    "braking_diagnostics":summarize_braking(self._timeline),
                    "legacy_inspired_wait":self._approach_wait.report(),
                    "legacy_event_projection":{"contract":"observed_vehicle_body_centerline_v1",
                        "vehicle_passages":len(self._centerline_seen),
                        "vehicle_journey_ids":sorted(self._centerline_seen),
                        "pedestrian_gate_crossings":self._metrics.summary()["pedestrian_crossings"],
                        "legacy_queue_wait_equivalent":False,"matched_demand":False,
                        "production_experiment_parity":False}} if self._geometry in MIDBLOCK_GEOMETRIES else {}),
                "trip_accounting":self._trip_accounting(),
                "unknown_roads":sorted(self._routes.unknown_roads),"arrived_vehicles":sorted(self._session.arrived),
                "arrived_pedestrians":sorted(self._session.person_arrived),
                "production_experiment_parity":False,"physical_output_allowed":False}

    def view_scene(self, *, epoch, generation, tick, source_id, _include_lanes=True):
        """Exact native scene in a requested image plane; canonical editor is untouched."""
        with self._lock:
            self._require(epoch,generation,tick)
            if source_id not in VIEW_FLIPS:
                raise AppError(ErrorCode.CAMERA_SOURCE_INVALID,"Unknown native evaluation view.",status_code=422)
            scene=self.scene(source_id=source_id,_include_lanes=_include_lanes)["snapshot"]
            identity = synthetic_scene_identity(
                epoch=epoch,generation=generation,tick=tick,
                source_id=evaluation_source_id(ENGINES[self._engine],generation,source_id),view_id=source_id,
                frame_number=tick,received_at_ms=self._received_at_ms,
                coordinate_space=scene["coordinate_space"],layout_id=scene["layout_id"],
                width=scene["width"],height=scene["height"],provenance=ENGINES[self._engine],
                tick_kind="native_fixed_step" if self._engine=="native" else "reference_fixed_step")
            if self._geometry in MIDBLOCK_GEOMETRIES:
                identity.update(simulation_engine="native",demand_model=scene["demand_model"],demand_digest=scene["demand_digest"],agent_anchor="native_front_center_footprints_v1")
            return {**scene,"view_id":source_id,"source_id":identity["source_id"],
                    "frame_number":tick,"legacy_editor_compatible":False,"observation":identity}

    def evaluate_region(self, *, epoch, generation, tick, source_id, coordinate_space, layout_id, polygon):
        with self._lock:
            self._require(epoch,generation,tick)
            if coordinate_space!="native_projection_v1" or layout_id!=self._projection.layout_id:
                raise self._conflict("Region coordinate space or layout does not match native geometry.")
            scene=self.view_scene(epoch=epoch,generation=generation,tick=tick,source_id=source_id,_include_lanes=False)
            try:
                result=region_counts(scene,polygon)
            except (ValueError,TypeError) as exc:
                raise AppError(ErrorCode.INVALID_REQUEST,str(exc),status_code=422) from exc
            # Mirror within this layout only. Never translate a saved legacy polygon.
            layout=self._projection.layout
            world=[layout.world(*pt,source_id) for pt in result["polygon"]]
            return {"epoch":epoch,"generation":generation,"tick":tick,"source_id":source_id,
                    "coordinate_space":coordinate_space,"layout_id":layout_id,**result,
                    "polygon_world_m":world,"observation":scene["observation"],
                    "provenance":"synthetic_native_region_evaluation" if self._engine=="native" else "synthetic_reference_region_evaluation","engine":self._engine,"persisted":False,"physical_output_allowed":False}

    def evaluate_region_views(self, *, epoch,generation,tick,source_id,coordinate_space,layout_id,polygon):
        """One draft, one exact native tick, four mirrored image planes.

        Never persist or translate a saved legacy zone. Point counts use the
        existing front/centre anchor contract, not body intersection.
        """
        with self._lock:
            original=self.evaluate_region(epoch=epoch,generation=generation,tick=tick,source_id=source_id,
                coordinate_space=coordinate_space,layout_id=layout_id,polygon=polygon)
            if any(not (0<=x<=1279 and 0<=y<=719) for x,y in original["polygon"]):
                raise AppError(ErrorCode.INVALID_REQUEST,"Draft vertices must lie within mirrorable pixel centres.",status_code=422)
            canonical=[list(simulation_view_point(x,y,1280,720,source_id)) for x,y in original["polygon"]]
            views={}
            for sid in VIEW_FLIPS:
                mirrored=[simulation_view_point(x,y,1280,720,sid) for x,y in canonical]
                result=original if sid==source_id else self.evaluate_region(epoch=epoch,generation=generation,tick=tick,source_id=sid,
                    coordinate_space=coordinate_space,layout_id=layout_id,polygon=mirrored)
                if result["agent_ids"]!=original["agent_ids"] or result["counts"]!=original["counts"]:
                    raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED,"Native draft view identity mismatch.",status_code=503)
                views[sid]={"polygon":result["polygon"],"counts":result["counts"],
                            "agent_ids":result["agent_ids"],"observation":result["observation"]}
            profile={"schema_version":1,"coordinate_space":coordinate_space,"layout_id":layout_id,
                     "canonical_polygon":canonical,"count_basis":"observed_agent_anchor","detector_input_eligible":False}
            return {**original,"canonical_polygon":canonical,"views":views,"count_basis":"observed_agent_anchor",
                    "legacy_editor_compatible":False,"region_profile":profile}

    def preview_legacy_rectangle(self,*,epoch,generation,tick,source_id,legacy_layout_id,layout_id,polygon):
        """Read-only semantic preview; original saved geometry is never written."""
        with self._lock:
            self._require(epoch,generation,tick)
            if legacy_layout_id!=LEGACY_LAYOUT_ID or layout_id!=self._projection.layout_id:
                raise self._conflict("Legacy or native preview layout mismatch.")
            if source_id not in VIEW_FLIPS:
                raise AppError(ErrorCode.CAMERA_SOURCE_INVALID,"Unknown native evaluation view.",status_code=422)
            try:
                mapping=legacy_rectangle_preview(self.scene()["snapshot"],polygon,source_id)
            except (ValueError,TypeError) as exc:
                raise AppError(ErrorCode.INVALID_REQUEST,str(exc),status_code=422) from exc
            result=self.evaluate_region_views(epoch=epoch,generation=generation,tick=tick,source_id=source_id,
                coordinate_space="native_projection_v1",layout_id=layout_id,polygon=mapping["polygon"])
            annotations=footprint_annotations(self.scene()["snapshot"])
            box_counts=footprint_center_counts(annotations,mapping["polygon"],source_id)
            return {"mapping":mapping,"evaluation":result,"synthetic_box_center_evaluation":box_counts,"legacy_layout_id":legacy_layout_id,
                    "native_layout_id":layout_id,"production_coordinate_parity":False}

    def evaluate_region_profile(self,*,epoch,generation,tick,source_id,profile):
        """Explicitly reuse a native-only profile across equivalent layouts.
        Never convert a legacy zone or accept a detector-eligible profile.
        """
        with self._lock:
            self._require(epoch,generation,tick)
            if source_id not in VIEW_FLIPS:
                raise AppError(ErrorCode.CAMERA_SOURCE_INVALID,"Unknown native evaluation view.",status_code=422)
            if (profile.get("schema_version")!=1 or profile.get("coordinate_space")!="native_projection_v1" or
                profile.get("layout_id")!=self._projection.layout_id or profile.get("count_basis")!="observed_agent_anchor" or
                profile.get("detector_input_eligible") is not False):
                raise self._conflict("Native region profile is incompatible with this layout or authority.")
            canonical=[[float(x),float(y)] for x,y in profile["canonical_polygon"]]
            if any(not (0<=x<=1279 and 0<=y<=719) for x,y in canonical):
                raise AppError(ErrorCode.INVALID_REQUEST,"Native profile vertices outside mirrorable pixel centres.",status_code=422)
            polygon=[simulation_view_point(x,y,1280,720,source_id) for x,y in canonical]
            result=self.evaluate_region_views(epoch=epoch,generation=generation,tick=tick,source_id=source_id,
                coordinate_space=profile["coordinate_space"],layout_id=profile["layout_id"],polygon=polygon)
            # Double mirroring fractional coordinates may introduce roundoff.
            # Preserve the original validated canonical JSON coordinates, not a
            # repeatedly transformed approximation or a tuple/list mismatch.
            if any(not math.isclose(a,b,rel_tol=0.,abs_tol=1e-9)
                   for p,q in zip(canonical,result["canonical_polygon"]) for a,b in zip(p,q)):
                raise self._conflict("Native profile canonical transform mismatch.")
            result["canonical_polygon"]=canonical
            result["region_profile"]["canonical_polygon"]=deepcopy(canonical)
            return result

    def compare(self, *, epoch, generation, density, seed, duration_seconds, profile=None, geometry='standard', engine='native'):
        """Run a bounded pair with one immutable copy of the saved policy.

        Only when standalone evaluation is idle. No changes to the saved profile,
        existing experiment store or selected camera. Reserve a child session
        under lock, then release the lock so state reads remain responsive.
        """
        with self._lock:
            self._require(epoch,generation,running=False)
            if self._state == "running":
                raise self._conflict("Stop the active native evaluation before comparing policies.")
            if engine not in ENGINES or not valid_geometry(engine,geometry) or density not in DENSITY_COUNTS or type(seed) is not int or not 0<=seed<=2**31-1 or type(duration_seconds) is not int or not 30<=duration_seconds<=500:
                raise AppError(ErrorCode.INVALID_REQUEST,"Invalid native comparison settings.",status_code=422)
            policy=deepcopy(signal_rules_service.get_config())
            selected=profile or policy.get("active_profile")
            if selected not in policy.get("profiles",{}):
                raise AppError(ErrorCode.INVALID_REQUEST,"Unknown experiment policy profile.",status_code=422)
            policy["active_profile"]=selected
            pair={}
            child=NativeEvaluationService(enabled=True,factory=self._factory,
                trip_loader=self._trip_loader,phase_loader=self._phase_loader,reference_factory=self._reference_factory,midblock_factory=self._midblock_factory,indexed_frames=self._indexed_frames)
            cancelled=Event()
            reservation=(cancelled,child)
            previous_state=self._state
            self._comparison=reservation
            self._state="busy"
        try:
            try:
                for mode in ("fixed","adaptive"):
                    # Serialize the final cancellation check with child startup.
                    # Shutdown cannot finish reaping and then see a new child.
                    with child._lock:
                        if cancelled.is_set():
                            raise self._conflict("Native comparison cancelled.")
                        initial=child.start(epoch=child.epoch,generation=child.generation,density=density,
                            seed=seed,mode=mode,policy_config=policy,profile=selected,geometry=geometry,engine=engine)
                    gen=initial["generation"]
                    horizon=duration_seconds*5
                    for tick in range(0,horizon,MAX_BATCH):
                        if cancelled.is_set():
                            raise self._conflict("Native comparison cancelled.")
                        child.step(epoch=child.epoch,generation=gen,tick=tick,steps=min(MAX_BATCH,horizon-tick),_return_scene=False)
                    pair[mode]=child.export(epoch=child.epoch,generation=gen,tick=horizon)
                    child.stop(epoch=child.epoch,generation=gen)
            finally:
                child.close()
            if cancelled.is_set():
                raise self._conflict("Native comparison cancelled.")
            try:
                deltas=validate_pair(pair["fixed"],pair["adaptive"])
            except ValueError as exc:
                raise AppError(ErrorCode.INVALID_REQUEST,str(exc),status_code=409) from exc
            meta={"schema_version":1,"engine":engine,"evidence":"executed_synthetic_native_comparison" if engine=="native" else "executed_synthetic_reference_comparison",
                "metric_contract":"normalized_physical_service_gate_v1","coordinate_space":"native_projection_v1",
                "layout_id":pair["fixed"]["layout_id"],"geometry":geometry,"profile":selected,"density":density,"seed":seed,
                **({"demand_model":"native_cyclic_slots_v1"} if geometry in MIDBLOCK_GEOMETRIES else {}),
                "duration_seconds":duration_seconds,"demand_digest":pair["fixed"]["demand_digest"],"policy_sha256":hashlib.sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest(),
                "production_experiment_parity":False,"physical_output_allowed":False,
                "limitations":("Same cyclic slot specification and saved policy, not matched journey counts or legacy pixel geometry. Reentry requires native arrival; unfinished visits retained." if geometry in MIDBLOCK_GEOMETRIES else "Same finite demand and saved policy copy, not legacy metric parity. Wait is queued agent-seconds; unfinished journeys and censored visits retained. Reference uses constant-speed/gap model, not SUMO or production legacy.")}
            stream=BytesIO()
            with ZipFile(stream,"w") as z:
                z.writestr("manifest.json",json.dumps(meta,indent=2))
                z.writestr("policy.json",json.dumps(policy,indent=2))
                z.writestr("fixed.json",json.dumps(pair["fixed"],indent=2))
                z.writestr("adaptive.json",json.dumps(pair["adaptive"],indent=2))
                z.writestr("normalized_gate_comparison.csv",serialize_experiment_timeline(pair))
                z.writestr("deltas.json",json.dumps(deltas,indent=2))
            return stream.getvalue()
        finally:
            with self._lock:
                if self._comparison is reservation:
                    self._comparison=None
                    if self._state=="busy":
                        self._state=previous_state



native_evaluation_service = NativeEvaluationService(enabled=os.getenv("MESH_SUMO_NATIVE_EVALUATION")=="1")
