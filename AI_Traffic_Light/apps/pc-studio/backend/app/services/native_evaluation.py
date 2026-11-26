"""Manually stepped native-only evaluation; never a selected camera or physical controller."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from io import BytesIO
import json
import hashlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
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
from app.services.native_evaluation_geometry import region_counts
from app.services.native_evaluation_experiments import summarize_timeline, validate_pair

MAX_TICKS = 2500
MAX_BATCH = 25


class NativeEvaluationService:
    def __init__(self, *, enabled=False, factory=GeneratedSession, trip_loader=load_trips, phase_loader=PhaseMap.load):
        self.enabled = enabled
        self._factory, self._trip_loader, self._phase_loader = factory, trip_loader, phase_loader
        self._lock = RLock()
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
        self._geometry = None

    @staticmethod
    def _conflict(message):
        return AppError(ErrorCode.CAMERA_STREAM_NOT_STARTED, message, status_code=409)

    def _require(self, epoch, generation, tick=None, *, running=True):
        if not self.enabled:
            raise self._conflict("Standalone native evaluation is disabled.")
        if epoch != self.epoch or generation != self.generation:
            raise self._conflict("Retired native evaluation generation.")
        if running and self._state != "running":
            raise self._conflict("No active native evaluation.")
        if tick is not None and (self._adapter is None or self._adapter.snapshot().tick != tick):
            raise self._conflict("Retired native evaluation tick.")

    def _retire(self, state="idle"):
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
        self._geometry = None
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

    def start(self, *, epoch, generation, density, seed, mode, policy_config=None, profile=None, geometry='standard'):
        with self._lock:
            self._require(epoch, generation, running=False)
            if geometry not in GEOMETRY_PRESETS or density not in DENSITY_COUNTS or mode not in ("fixed", "adaptive") or type(seed) is not int or not 0 <= seed <= 2**31-1:
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
                def open_session(value):
                    kwargs = {'density': density}
                    if geometry != 'standard':
                        kwargs['geometry'] = geometry
                    self._session = self._factory(value, **kwargs)
                    return self._session
                self._adapter = SumoShadowAdapter(open_session)
                self._adapter.reset(seed=seed)
                network = self._session.network_path
                self._projection = NativeProjection(Projection.load(network), self.generation)
                trips = self._trip_loader(network, network.parent/"routes.xml")
                self._routes = RouteGateAdapter(trips)
                self._demand_digest = hashlib.sha256(json.dumps([asdict(t) for t in trips],sort_keys=True,separators=(",",":")).encode()).hexdigest()
                self._phase_map = self._phase_loader(network)
                self._metrics = GateMetrics()
                self._publisher.begin(self.generation)
                self._received_at_ms = time.time_ns() // 1_000_000
                self._density, self._mode = density, mode
                self._geometry = geometry
                self._state = "running"
                return self.scene()
            except Exception as exc:
                raise self._failure() from exc

    def step(self, *, epoch, generation, tick, steps, _return_scene=True):
        with self._lock:
            self._require(epoch, generation, tick)
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
                    permission = self._session.last_permission
                    vehicle_inside=any(a.kind=="vehicle" and a.road_id.startswith(":C_") for a in before.agents)
                    expected=self._phase_map.state(phase,vehicle_inside=vehicle_inside,pedestrian_inside=bool(crossing))
                    if permission!=expected:
                        raise RuntimeError("Native permission differs from protected phase map")
                    grants = {i for i,c in enumerate(permission) if c=="G"}
                    if (grants.intersection(self._phase_map.vehicles) and grants.intersection(self._phase_map.pedestrians) or
                        grants and phase not in ("vehicle_green","pedestrian_green") or
                        grants.intersection(self._phase_map.vehicles) and (crossing or phase!="vehicle_green") or
                        grants.intersection(self._phase_map.pedestrians) and phase!="pedestrian_green"):
                        raise RuntimeError("Invalid native permission")
                    measured = self._metrics.sample(snap.tick,self._routes.observations(snap.agents))
                    self._timeline.append({**measured,"phase":phase,"t":measured["t_seconds"],
                        "active_rules":list(signal.get("active_rules",[])),"applied_permission":permission,
                        "vehicle_trip_arrivals":len(self._session.arrived),"pedestrian_trip_arrivals":len(self._session.person_arrived)})
                    self._signal = {"phase":phase,"vehicle_go":signal["vehicle_go"],
                        "pedestrian_walk":signal["pedestrian_walk"],"seconds_remaining":signal["seconds_remaining"],
                        "applied_permission":permission,
                        "applied_vehicle_go":bool(grants.intersection(self._phase_map.vehicles)),
                        "applied_pedestrian_walk":bool(grants.intersection(self._phase_map.pedestrians))}
                self._received_at_ms = time.time_ns() // 1_000_000
                return self.scene() if _return_scene else None
            except Exception as exc:
                raise self._failure() from exc

    def pause(self, *, epoch, generation, tick, paused):
        with self._lock:
            self._require(epoch,generation,tick)
            if type(paused) is not bool:
                raise AppError(ErrorCode.INVALID_REQUEST, "Pause must be boolean.", status_code=422)
            self._paused = paused
            return self.scene()

    def stop(self, *, epoch, generation):
        with self._lock:
            self._require(epoch,generation,running=False)
            self._retire()
            return self.scene()

    def close(self):
        with self._lock:
            self._retire("idle" if self.enabled else "disabled")

    def scene(self, *, source_id="simulation_camera"):
        with self._lock:
            snapshot = None
            if self._state == "running":
                snap = self._adapter.snapshot()
                snapshot = {**self._projection.scene(snap, source_id),"received_at_ms":self._received_at_ms,
                    "paused":self._paused,"density":self._density,"geometry":self._geometry,"signal":deepcopy(self._signal),
                    "epoch":self.epoch,"profile":self._policy["active_profile"],
                    "legacy_editor_compatible":False}
            return {"status":self._state,"provenance":PROVENANCE,"epoch":self.epoch,
                "generation":self.generation,"snapshot":snapshot,"mode":self._mode,
                "density":self._density,"geometry":self._geometry,"max_ticks":MAX_TICKS,"native_only":True,
                "profile":self._policy["active_profile"] if self._policy else None,"physical_output_allowed":False}

    def _ensure_frames(self):
        snap = self._adapter.snapshot()
        frame = self._publisher.frame_for("simulation_camera")
        if frame is None or frame.frame_number != snap.tick:
            meta, views = self._projection.render(snap)
            self._publisher.publish(meta,views,received_at_ms=self._received_at_ms)

    def frame(self, *, epoch, generation, tick, source_id):
        with self._lock:
            self._require(epoch,generation,tick)
            if source_id not in VIEW_FLIPS:
                raise AppError(ErrorCode.CAMERA_SOURCE_INVALID, "Unknown native evaluation view.", status_code=422)
            try:
                self._ensure_frames()
                return self._publisher.frame_for(source_id)
            except Exception as exc:
                raise self._failure() from exc

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
                        for sid in VIEW_FLIPS:
                            frame=self._publisher.frame_for(sid)
                            rec=writer.capture_frame(frame,session_id="native_evaluation")
                            z.writestr(sid+".png",(writer.dataset_root/rec.image_path).read_bytes())
                            z.writestr(sid+".json",(writer.dataset_root/rec.metadata_path).read_bytes())
                        meta=self.scene()["snapshot"]
                        z.writestr("scene.json",json.dumps(meta,indent=2))
                        z.writestr("coordinate_contract.json",json.dumps({"epoch":epoch,"generation":generation,"tick":tick,"layout_id":meta["layout_id"],"coordinate_space":meta["coordinate_space"],"width":1280,"height":720,"views":list(VIEW_FLIPS),"legacy_editor_compatible":False},indent=2))
                        z.writestr("agents.csv",export_csv(meta))
                    return stream.getvalue()
            except Exception as exc:
                raise self._failure() from exc

    def export(self, *, epoch, generation, tick):
        with self._lock:
            self._require(epoch,generation,tick)
            return {"schema_version":1,"provenance":"synthetic_native_gate_evaluation",
                "metric_contract":"normalized_physical_service_gate_v1","seed":self._adapter.snapshot().seed,
                "mode":self._mode,"density":self._density,"geometry":self._geometry,"step_s":STEP_S,"summary":self._metrics.summary(),
                "timeline":deepcopy(self._timeline),"observed_routes":deepcopy(self._routes.seen_roads),
                "layout_id":self._projection.layout_id,"coordinate_space":"native_projection_v1",
                "policy_config":deepcopy(self._policy),"legacy_editor_compatible":False,
                "demand_digest":self._demand_digest,"derived_metrics":summarize_timeline(self._timeline,self._metrics.summary()),
                "waiting_episodes":self._metrics.waiting_episodes(),
                "unknown_roads":sorted(self._routes.unknown_roads),"arrived_vehicles":sorted(self._session.arrived),
                "arrived_pedestrians":sorted(self._session.person_arrived),
                "production_experiment_parity":False,"physical_output_allowed":False}

    def view_scene(self, *, epoch, generation, tick, source_id):
        """Exact native scene in a requested image plane; canonical editor is untouched."""
        with self._lock:
            self._require(epoch,generation,tick)
            if source_id not in VIEW_FLIPS:
                raise AppError(ErrorCode.CAMERA_SOURCE_INVALID,"Unknown native evaluation view.",status_code=422)
            scene=self.scene(source_id=source_id)["snapshot"]
            return {**scene,"view_id":source_id,"source_id":f"native_eval_g{generation}_{source_id}",
                    "frame_number":tick,"legacy_editor_compatible":False}

    def evaluate_region(self, *, epoch, generation, tick, source_id, coordinate_space, layout_id, polygon):
        with self._lock:
            self._require(epoch,generation,tick)
            if coordinate_space!="native_projection_v1" or layout_id!=self._projection.layout_id:
                raise self._conflict("Region coordinate space or layout does not match native geometry.")
            scene=self.view_scene(epoch=epoch,generation=generation,tick=tick,source_id=source_id)
            try:
                result=region_counts(scene,polygon)
            except (ValueError,TypeError) as exc:
                raise AppError(ErrorCode.INVALID_REQUEST,str(exc),status_code=422) from exc
            return {"epoch":epoch,"generation":generation,"tick":tick,"source_id":source_id,
                    "coordinate_space":coordinate_space,"layout_id":layout_id,**result,
                    "provenance":"synthetic_native_region_evaluation","persisted":False,"physical_output_allowed":False}

    def compare(self, *, epoch, generation, density, seed, duration_seconds, profile=None, geometry='standard'):
        """Run a bounded pair with one immutable copy of the saved policy.

        Only when standalone evaluation is idle. No changes to the saved profile,
        existing experiment store or selected camera. Hold the service lock so
        another native session cannot start during this paired experiment.
        """
        with self._lock:
            self._require(epoch,generation,running=False)
            if self._state == "running":
                raise self._conflict("Stop the active native evaluation before comparing policies.")
            if geometry not in GEOMETRY_PRESETS or density not in DENSITY_COUNTS or type(seed) is not int or not 0<=seed<=2**31-1 or type(duration_seconds) is not int or not 30<=duration_seconds<=500:
                raise AppError(ErrorCode.INVALID_REQUEST,"Invalid native comparison settings.",status_code=422)
            policy=deepcopy(signal_rules_service.get_config())
            selected=profile or policy.get("active_profile")
            if selected not in policy.get("profiles",{}):
                raise AppError(ErrorCode.INVALID_REQUEST,"Unknown experiment policy profile.",status_code=422)
            policy["active_profile"]=selected
            pair={}
            child=NativeEvaluationService(enabled=True,factory=self._factory,
                trip_loader=self._trip_loader,phase_loader=self._phase_loader)
            try:
                for mode in ("fixed","adaptive"):
                    initial=child.start(epoch=child.epoch,generation=child.generation,density=density,
                        seed=seed,mode=mode,policy_config=policy,profile=selected,geometry=geometry)
                    gen=initial["generation"]
                    horizon=duration_seconds*5
                    for tick in range(0,horizon,MAX_BATCH):
                        child.step(epoch=child.epoch,generation=gen,tick=tick,steps=min(MAX_BATCH,horizon-tick),_return_scene=False)
                    pair[mode]=child.export(epoch=child.epoch,generation=gen,tick=horizon)
                    child.stop(epoch=child.epoch,generation=gen)
            finally:
                child.close()
            try:
                deltas=validate_pair(pair["fixed"],pair["adaptive"])
            except ValueError as exc:
                raise AppError(ErrorCode.INVALID_REQUEST,str(exc),status_code=409) from exc
            meta={"schema_version":1,"evidence":"executed_synthetic_native_comparison",
                "metric_contract":"normalized_physical_service_gate_v1","coordinate_space":"native_projection_v1",
                "layout_id":pair["fixed"]["layout_id"],"geometry":geometry,"profile":selected,"density":density,"seed":seed,
                "duration_seconds":duration_seconds,"demand_digest":pair["fixed"]["demand_digest"],"policy_sha256":hashlib.sha256(json.dumps(policy,sort_keys=True).encode()).hexdigest(),
                "production_experiment_parity":False,"physical_output_allowed":False,
                "limitations":"Same native finite demand and saved policy copy, not legacy metric parity. Wait is queued agent-seconds; unfinished journeys and censored visits retained."}
            stream=BytesIO()
            with ZipFile(stream,"w") as z:
                z.writestr("manifest.json",json.dumps(meta,indent=2))
                z.writestr("policy.json",json.dumps(policy,indent=2))
                z.writestr("fixed.json",json.dumps(pair["fixed"],indent=2))
                z.writestr("adaptive.json",json.dumps(pair["adaptive"],indent=2))
                z.writestr("normalized_gate_comparison.csv",serialize_experiment_timeline(pair))
                z.writestr("deltas.json",json.dumps(deltas,indent=2))
            return stream.getvalue()


native_evaluation_service = NativeEvaluationService(enabled=os.getenv("MESH_SUMO_NATIVE_EVALUATION")=="1")
