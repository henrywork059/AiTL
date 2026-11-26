"""Manually stepped native-only evaluation; never a selected camera or physical controller."""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
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
from app.services.simulation_finite_fixture import load_trips, RouteGateAdapter
from app.services.simulation_gate_metrics import GateMetrics, STEP_S
from app.services.sumo_frame_publisher import NativeFramePublisher
from app.services.sumo_projection import NativeProjection, Projection, PROVENANCE, VIEW_FLIPS, export_csv
from app.services.sumo_shadow_adapter import SumoShadowAdapter
from app.services.sumo_shadow_fixture import DENSITY_COUNTS, PHASES, PhaseMap
from app.services.sumo_shadow_runtime import GeneratedSession

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

    def start(self, *, epoch, generation, density, seed, mode):
        with self._lock:
            self._require(epoch, generation, running=False)
            if density not in DENSITY_COUNTS or mode not in ("fixed", "adaptive") or type(seed) is not int or not 0 <= seed <= 2**31-1:
                raise AppError(ErrorCode.INVALID_REQUEST, "Invalid native evaluation settings.", status_code=422)
            try:
                self._retire()
                self._temp = TemporaryDirectory(prefix="mesh-native-evaluation-")
                folder = Path(self._temp.name)
                self._controller = _BenchmarkSignalRulesService(config_path=folder/"signals.json",
                    history_path=folder/"history.jsonl", respect_environment=False)
                config = self._controller.defaults()
                config["mode"] = mode
                config["dry_run"] = False
                self._controller.save_config(config)
                self._controller.reset_runtime(0.)
                def open_session(value):
                    self._session = self._factory(value, density=density)
                    return self._session
                self._adapter = SumoShadowAdapter(open_session)
                self._adapter.reset(seed=seed)
                network = self._session.network_path
                self._projection = NativeProjection(Projection.load(network), self.generation)
                self._routes = RouteGateAdapter(self._trip_loader(network, network.parent/"routes.xml"))
                self._phase_map = self._phase_loader(network)
                self._metrics = GateMetrics()
                self._publisher.begin(self.generation)
                self._received_at_ms = time.time_ns() // 1_000_000
                self._density, self._mode = density, mode
                self._state = "running"
                return self.scene()
            except Exception as exc:
                raise self._failure() from exc

    def step(self, *, epoch, generation, tick, steps):
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
                        "applied_permission":permission}
                self._received_at_ms = time.time_ns() // 1_000_000
                return self.scene()
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

    def scene(self):
        with self._lock:
            snapshot = None
            if self._state == "running":
                snap = self._adapter.snapshot()
                snapshot = {**self._projection.scene(snap),"received_at_ms":self._received_at_ms,
                    "paused":self._paused,"density":self._density,"signal":deepcopy(self._signal)}
            return {"status":self._state,"provenance":PROVENANCE,"epoch":self.epoch,
                "generation":self.generation,"snapshot":snapshot,"mode":self._mode,
                "density":self._density,"max_ticks":MAX_TICKS,"native_only":True,"physical_output_allowed":False}

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
                        z.writestr("agents.csv",export_csv(meta))
                    return stream.getvalue()
            except Exception as exc:
                raise self._failure() from exc

    def export(self, *, epoch, generation, tick):
        with self._lock:
            self._require(epoch,generation,tick)
            return {"schema_version":1,"provenance":"synthetic_native_gate_evaluation",
                "metric_contract":"normalized_physical_service_gate_v1","seed":self._adapter.snapshot().seed,
                "mode":self._mode,"density":self._density,"step_s":STEP_S,"summary":self._metrics.summary(),
                "timeline":deepcopy(self._timeline),"observed_routes":deepcopy(self._routes.seen_roads),
                "unknown_roads":sorted(self._routes.unknown_roads),"arrived_vehicles":sorted(self._session.arrived),
                "arrived_pedestrians":sorted(self._session.person_arrived),
                "production_experiment_parity":False,"physical_output_allowed":False}


native_evaluation_service = NativeEvaluationService(enabled=os.getenv("MESH_SUMO_NATIVE_EVALUATION")=="1")
