"""Offline native evaluation API and isolated capture tests."""
from pathlib import Path
import io
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"apps/pc-studio/backend"))
from fastapi.testclient import TestClient
from test_camera_simulation_api import build_test_app, assert_envelope
from app.routes import camera as routes
from app.routes import experiments as experiment_routes
from app.services.signal_rules import SignalRulesService
from app.services.camera_frames import CameraFrameService
from app.services.zones import ZoneService
from app.services.native_evaluation import NativeEvaluationService
from app.services.simulation_finite_fixture import Segment,Trip
from app.services.sumo_shadow_adapter import ShadowAgent
from app.services.sumo_shadow_fixture import PhaseMap
from app.services.sumo_projection import VIEW_FLIPS

BASE="/api/camera/simulation/native-evaluation"


class FakeSession:
    def __init__(self,path):
        self.network_path=path
        self.tick=0
        self.closed=False
        self.arrived=set()
        self.person_arrived=set()
        self.last_permission="rr"
    def set_phase(self,phase):
        self.last_permission="Gr" if phase=="vehicle_green" else "rG" if phase=="pedestrian_green" else "rr"
    def advance(self):
        self.tick+=1
    def agents(self):
        return (ShadowAgent("vehicle","v0",min(19.,self.tick*.2),0.,1.,"WC"),)
    def close(self):
        self.closed=True


class Tests(unittest.TestCase):
    def test_disabled(self):
        with patch.object(routes,"native_evaluation_service",NativeEvaluationService()),TestClient(build_test_app()) as client:
            data=assert_envelope(client.get(BASE))["data"]
            self.assertEqual(data["status"],"disabled")
            assert_envelope(client.post(BASE+"/start",json={"epoch":data["epoch"],"generation":data["generation"]}),expected_status=409)

    def test_camera_workspace_lease_isolation_and_expiry(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"network.xml"
            path.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            trips=(Trip("v0","vehicle",0.,10.,(Segment("WC","road",((0.,0.),(20.,0.))),)),)
            mapping=PhaseMap((("a","b",""),("c","d","")),(0,),(1,),frozenset())
            sessions=[]
            def factory(seed,*,density):
                x=FakeSession(path);sessions.append(x);return x
            service=NativeEvaluationService(enabled=True,factory=factory,trip_loader=lambda *args:trips,
                phase_loader=lambda _:mapping,camera_lease_seconds=10.)
            self.addCleanup(service.close)
            legacy=CameraFrameService(simulation_seed=42,simulation_monotonic=lambda:0.)
            legacy.set_simulation(True)
            legacy.configure_simulation(paused=True)
            self.addCleanup(legacy.set_simulation,False)
            baseline=legacy.latest_frame()
            token=legacy.observation_mode_token
            a,b="a"*32,"b"*32
            with patch.object(routes,"native_evaluation_service",service),patch.object(routes,"camera_frame_service",legacy),TestClient(build_test_app()) as client:
                def ident():
                    x=service.scene();return {k:x[k] for k in ("epoch","generation")}
                def post(action,payload,expected_status=200):
                    return assert_envelope(client.post(BASE+"/"+action,json=payload),expected_status=expected_status)
                initial=ident()
                post("start",initial)
                standalone=ident()
                post("start",{**standalone,"camera_owner":a},409)
                self.assertFalse(sessions[-1].closed)
                post("stop",standalone)
                self.assertTrue(sessions[-1].closed)
                state=post("start",{**ident(),"camera_owner":a})["data"]
                self.assertTrue(state["camera_owned"])
                self.assertNotIn(a,json.dumps(state))
                owned=ident()
                for bad in ({}, {"camera_owner":b}):
                    post("start",{**owned,**bad},409)
                    post("step",{**owned,"tick":0,"steps":1,**bad},409)
                    post("pause",{**owned,"tick":0,"paused":True,**bad},409)
                    post("stop",{**owned,**bad},409)
                post("camera-heartbeat",{**owned,"camera_owner":b},409)
                post("camera-release",{"epoch":owned["epoch"],"camera_owner":b},409)
                post("camera-heartbeat",{**owned,"camera_owner":a})
                post("step",{**owned,"tick":0,"steps":1,"camera_owner":a})
                post("pause",{**owned,"tick":1,"paused":True,"camera_owner":a})
                frame=service.frame(**owned,tick=1,source_id="simulation_camera")
                self.assertFalse(frame.origin=="simulation")
                self.assertIs(legacy.latest_frame(),baseline)
                self.assertEqual(legacy.observation_mode_token,token)
                post("camera-release",{"epoch":owned["epoch"],"camera_owner":a})
                self.assertTrue(sessions[-1].closed)
                self.assertEqual(service.scene()["status"],"idle")
                post("camera-heartbeat",{**owned,"camera_owner":a},409)
                self.assertFalse(post("camera-release",{"epoch":owned["epoch"],"camera_owner":a})["data"]["released"])
                # Exercise actual timer-driven cleanup, including no subsequent client request.
                service._camera_lease_seconds=.2
                state=post("start",{**ident(),"camera_owner":b})["data"]
                retired=ident()
                deadline=time.monotonic()+3
                while not sessions[-1].closed and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(sessions[-1].closed)
                self.assertEqual(service.scene()["status"],"idle")
                self.assertFalse(service.scene()["camera_owned"])
                assert_envelope(client.get(BASE+"/frame",params={**retired,"tick":0,"source_id":"simulation_camera"}),expected_status=409)
                self.assertIs(legacy.latest_frame(),baseline)
                self.assertEqual(legacy.observation_mode_token,token)
                post("start",ident())
                self.assertFalse(service.scene()["camera_owned"])

    def test_midblock_lifecycle_and_dynamic_journey_export(self):
        from app.services.sumo_midblock_fixture import slots_for
        from app.services.sumo_midblock_session import CyclicLedger
        from dataclasses import asdict,replace
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"network.xml"
            path.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            slots=slots_for(42,"light")[:1]
            class CyclicFake(FakeSession):
                def __init__(self):
                    super().__init__(path)
                    self.ledger=CyclicLedger(slots)
                    self.phase_map=PhaseMap((("a","b",""),("c","d","")),(0,),(1,),frozenset())
                    self.trips=(Trip("v0_0","vehicle",0.,5.,(Segment("WC","road",((0.,0.),(20.,0.))),)),)
                @property
                def demand_manifest(self):
                    return [asdict(x) for x in slots]
                def occupied(self,agents): return False,False
                def agents(self):
                    return () if self.tick==2 else (ShadowAgent("vehicle","v0_0" if self.tick==1 else "v0_1",min(19.,self.tick*.2),0.,1.,"WC"),)
                def advance(self):
                    super().advance()
                    if self.tick==1:
                        self.ledger.reconcile(("v0_0",),(),.2)
                    if self.tick==2:
                        new=self.ledger.reconcile((),("v0_0",),.4)
                        self.arrived.add("v0_0")
                        self.trips+=tuple(replace(self.trips[0],ident=ident,depart_s=depart) for ident,depart in new)
            sessions=[]
            def factory(seed,*,density):
                session=CyclicFake()
                sessions.append(session)
                return session
            service=NativeEvaluationService(enabled=True,midblock_factory=factory)
            self.addCleanup(service.close)
            with patch.object(routes,"native_evaluation_service",service),TestClient(build_test_app()) as client:
                initial=service.scene()
                identity={k:initial[k] for k in ("epoch","generation")}
                assert_envelope(client.post(BASE+"/start",json={**identity,"geometry":"midblock","engine":"reference"}),expected_status=422)
                state=assert_envelope(client.post(BASE+"/start",json={**identity,"geometry":"midblock","density":"light"}))["data"]
                identity={k:state[k] for k in ("epoch","generation")}
                assert state["snapshot"]["demand_model"]=="native_cyclic_slots_v1"
                first=assert_envelope(client.post(BASE+"/step",json={**identity,"tick":0,"steps":1}))["data"]
                self.assertEqual(first["snapshot"]["agents"][0]["slot_id"],"v0")
                self.assertEqual(first["snapshot"]["agents"][0]["visit"],0)
                self.assertEqual(first["snapshot"]["agents"][0]["vehicle_type"],"car")
                self.assertEqual(first["snapshot"]["agents"][0]["length_m"],4.5)
                self.assertTrue(first["snapshot"]["agents"][0]["eastbound"])
                layout=first["snapshot"]["layout_id"]
                payload={**identity,"tick":1,"source_id":"simulation_camera_c","coordinate_space":"native_projection_v1","layout_id":layout,
                         "polygon":[[0,0],[1279,0],[1279,719],[0,719]]}
                all_views=assert_envelope(client.post(BASE+"/region/views",json=payload))["data"]
                self.assertEqual(set(all_views["views"]),set(VIEW_FLIPS))
                self.assertEqual(all_views["count_basis"],"observed_agent_anchor")
                self.assertFalse(all_views["persisted"])
                for sid,view in all_views["views"].items():
                    self.assertEqual(view["counts"],{"vehicle":1,"pedestrian":0})
                    self.assertEqual(view["agent_ids"],all_views["agent_ids"])
                    self.assertEqual(view["observation"]["view_id"],sid)
                    self.assertEqual(view["observation"]["demand_digest"],first["snapshot"]["demand_digest"])
                    self.assertFalse(view["observation"]["detector_input_eligible"])
                self.assertEqual(all_views["canonical_polygon"],[[1279,0],[0,0],[0,719],[1279,719]])
                profile=all_views["region_profile"]
                reuse={**identity,"tick":1,"source_id":"simulation_camera_b","profile":profile}
                loaded=assert_envelope(client.post(BASE+"/region/profile",json=reuse))["data"]
                self.assertEqual(loaded["agent_ids"],all_views["agent_ids"])
                self.assertEqual(loaded["canonical_polygon"],profile["canonical_polygon"])
                for bad in ({**profile,"layout_id":"0"*64},{**profile,"coordinate_space":"legacy_pixels"},{**profile,"detector_input_eligible":True}):
                    assert_envelope(client.post(BASE+"/region/profile",json={**reuse,"profile":bad}),expected_status=409)
                for bad in ({**payload,"layout_id":"0"*64},{**payload,"coordinate_space":"legacy_pixels"},{**payload,"tick":0}):
                    assert_envelope(client.post(BASE+"/region/views",json=bad),expected_status=409)
                assert_envelope(client.post(BASE+"/region/views",json={**payload,"polygon":[[0,0],[1279.5,0],[1279.5,719],[0,719]]}),expected_status=422)
                exact=client.get("/api/camera/simulation/observation/frame",params={**identity,"engine":"native","tick":1,"source_id":"simulation_camera_c","layout_id":layout})
                self.assertEqual(exact.status_code,200)
                self.assertEqual(exact.headers["x-observation-epoch"],identity["epoch"])
                self.assertEqual(exact.headers["x-layout-id"],layout)
                with ZipFile(io.BytesIO(service.capture(**identity,tick=1))) as z:
                    self.assertIn("slot_id,visit",z.read("agents.csv").decode())
                    self.assertEqual(json.loads(z.read("coordinate_contract.json"))["demand_digest"],first["snapshot"]["demand_digest"])
                    for sid in VIEW_FLIPS:
                        metadata=json.loads(z.read(sid+".json"))
                        self.assertEqual(metadata["simulation_engine"],"native")
                        self.assertEqual(metadata["simulation_demand_digest"],first["snapshot"]["demand_digest"])
                        self.assertEqual(metadata["origin"],"synthetic_sumo_projection")
                    self.assertEqual(exact.content,z.read("simulation_camera_c.png"))
                paused=assert_envelope(client.post(BASE+"/pause",json={**identity,"tick":1,"paused":True}))["data"]
                self.assertTrue(paused["snapshot"]["paused"])
                assert_envelope(client.post(BASE+"/step",json={**identity,"tick":1,"steps":1}),expected_status=409)
                assert_envelope(client.post(BASE+"/pause",json={**identity,"tick":1,"paused":False}))
                assert_envelope(client.post(BASE+"/step",json={**identity,"tick":1,"steps":1}))
                result=service.export(**identity,tick=2)
                self.assertEqual(result["demand_manifest"],[asdict(x) for x in slots])
                self.assertEqual(len(result["journey_manifest"]),2)
                self.assertEqual(result["trip_accounting"]["arrived"],["v0_0"])
                self.assertEqual(result["trip_accounting"]["not_yet_due"],["v0_1"])
                self.assertEqual(result["slot_visits"],{"v0":1})
                assert_envelope(client.post(BASE+"/stop",json=identity))
                self.assertTrue(sessions[0].closed)
                assert_envelope(client.get(BASE+"/frame",params={**identity,"tick":2,"source_id":"simulation_camera"}),expected_status=409)
                assert_envelope(client.post(BASE+"/region/views",json=payload),expected_status=409)
                restarted=assert_envelope(client.post(BASE+"/start",json={**{k:service.scene()[k] for k in ("epoch","generation")},"geometry":"midblock","density":"light"}))["data"]
                identity2={k:restarted[k] for k in ("epoch","generation")}
                assert_envelope(client.post(BASE+"/region/profile",json=reuse),expected_status=409)
                fresh=assert_envelope(client.post(BASE+"/region/profile",json={**reuse,**identity2,"tick":0}))["data"]
                self.assertEqual(fresh["region_profile"],profile)
                self.assertFalse(fresh["persisted"])

    def test_reference_switch_and_production_rollback(self):
        from app.services.simulation_reference_session import FiniteReferenceSession
        from app.services.observation_identity import REFERENCE_EVALUATION_ORIGIN
        from app.services.inference import InferenceService
        from app.core.exceptions import AppError
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            network=root/"network.xml"
            network.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            trips=(Trip("v0","vehicle",0.,10.,(Segment("WC","road",((0.,0.),(20.,0.))),)),)
            mapping=PhaseMap((("a","b",""),("c","d","")),(0,),(1,),frozenset())
            sessions=[]
            def factory(seed,*,density):
                session=FakeSession(network)
                sessions.append(session)
                return session
            def reference_factory(seed,*,density):
                session=FiniteReferenceSession(network,trips,mapping)
                sessions.append(session)
                return session
            service=NativeEvaluationService(enabled=True,factory=factory,
                trip_loader=lambda *args:trips,phase_loader=lambda _:mapping,
                reference_factory=reference_factory)
            self.addCleanup(service.close)
            legacy=CameraFrameService(simulation_seed=42,simulation_monotonic=lambda:0.)
            policy=SignalRulesService(config_path=root/"legacy-policy.json",history_path=root/"history.jsonl",respect_environment=False)
            policy.save_config(policy.defaults())
            with patch("app.services.camera_frames.signal_rules_service",policy), \
                 patch.object(routes,"camera_frame_service",legacy), \
                 patch.object(routes,"native_evaluation_service",service),TestClient(build_test_app()) as client:
                legacy.set_simulation(True)
                legacy.configure_simulation(paused=True)
                frame=legacy.latest_frame()
                token=legacy.observation_mode_token
                def start(engine):
                    identity={k:service.scene()[k] for k in ("epoch","generation")}
                    return assert_envelope(client.post(BASE+"/start",json={**identity,"engine":engine}))["data"]
                def advance(state,steps):
                    identity={k:state[k] for k in ("epoch","generation")}
                    return assert_envelope(client.post(BASE+"/step",json={**identity,"tick":state["snapshot"]["tick"],"steps":steps}))["data"]
                native=advance(start("native"),3)
                native_id={k:native[k] for k in ("epoch","generation")}
                native_result=service.export(**native_id,tick=3)
                native_frame=service.frame(**native_id,tick=3,source_id="simulation_camera")
                self.assertEqual(native_frame.origin,"synthetic_sumo_projection")
                ref=start("reference")
                self.assertTrue(sessions[0].closed)
                self.assertEqual(ref["snapshot"]["tick"],0)
                self.assertEqual(ref["snapshot"]["layout_id"],native["snapshot"]["layout_id"])
                self.assertEqual(ref["provenance"],REFERENCE_EVALUATION_ORIGIN)
                self.assertFalse(ref["native_only"])
                assert_envelope(client.get(BASE+"/frame",params={**native_id,"tick":3,"source_id":"simulation_camera"}),expected_status=409)
                ref=advance(ref,3)
                ref_id={k:ref[k] for k in ("epoch","generation")}
                ref_result=service.export(**ref_id,tick=3)
                self.assertEqual(ref_result["demand_digest"],native_result["demand_digest"])
                self.assertEqual(ref_result["demand_manifest"],native_result["demand_manifest"])
                self.assertEqual(ref_result["engine"],"reference")
                view=assert_envelope(client.get("/api/camera/simulation/observation",params={"engine":"reference"}))["data"]
                self.assertEqual(view["observation"]["provenance"],REFERENCE_EVALUATION_ORIGIN)
                self.assertFalse(view["observation"]["detector_input_eligible"])
                self.assertTrue(view["agents"][0]["id"].startswith("reference:"))
                exact={**ref_id,"engine":"reference","tick":3,"source_id":"simulation_camera","layout_id":ref["snapshot"]["layout_id"]}
                binary=client.get("/api/camera/simulation/observation/frame",params=exact)
                self.assertEqual(binary.status_code,200)
                self.assertEqual(binary.headers["x-observation-origin"],REFERENCE_EVALUATION_ORIGIN)
                self.assertTrue(binary.headers["x-camera-source"].startswith("reference_eval_"))
                assert_envelope(client.get("/api/camera/simulation/observation/frame",params={**exact,"engine":"native"}),expected_status=409)
                assert_envelope(client.get("/api/camera/simulation/observation",params={"engine":"native"}),expected_status=409)
                with self.assertRaises(AppError):
                    InferenceService().detect_frame(service.frame(**ref_id,tick=3,source_id="simulation_camera"))
                with ZipFile(io.BytesIO(service.capture(**ref_id,tick=3))) as z:
                    self.assertEqual(json.loads(z.read("coordinate_contract.json"))["engine"],"reference")
                    self.assertEqual(json.loads(z.read("simulation_camera.json"))["origin"],REFERENCE_EVALUATION_ORIGIN)
                    self.assertEqual(z.read("simulation_camera.png"),binary.content)
                self.assertIs(legacy.latest_frame(),frame)
                self.assertEqual(legacy.observation_mode_token,token)
                restored=start("native")
                self.assertTrue(sessions[1].closed)
                self.assertEqual(restored["snapshot"]["tick"],0)
                self.assertEqual(restored["snapshot"]["layout_id"],native["snapshot"]["layout_id"])
                assert_envelope(client.get("/api/camera/simulation/observation/frame",params=exact),expected_status=409)
                restored=advance(restored,3)
                self.assertEqual(restored["snapshot"]["agents"],native["snapshot"]["agents"])
                with patch.object(sessions[-1],"advance",side_effect=RuntimeError("fixture failure")):
                    assert_envelope(client.post(BASE+"/step",json={"epoch":restored["epoch"],"generation":restored["generation"],"tick":3,"steps":1}),expected_status=503)
                self.assertTrue(sessions[-1].closed)
                self.assertIsNone(service.scene()["snapshot"])
                self.assertIs(legacy.latest_frame(),frame)
                self.assertEqual(legacy.observation_mode_token,token)
                legacy.set_simulation(False)

    def test_lifecycle_capture_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            network=root/"network.xml"
            network.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            sessions=[]
            def factory(seed,*,density):
                obj=FakeSession(network)
                sessions.append(obj)
                return obj
            trips=(Trip("v0","vehicle",0.,10.,(Segment("WC","road",((0.,0.),(20.,0.))),)),)
            service=NativeEvaluationService(enabled=True,factory=factory,trip_loader=lambda *args:trips,
                phase_loader=lambda _:PhaseMap((("a","b",""),("c","d","")),(0,),(1,),frozenset()))
            self.addCleanup(service.close)
            sentinel=root/"never-write.json"
            with patch.dict(os.environ,{"AITL_SIGNAL_RULES":str(sentinel),"AITL_DATASET_DIR":str(root/"never-dataset")}), \
                 patch.object(routes,"native_evaluation_service",service), TestClient(build_test_app()) as client:
                state=assert_envelope(client.get(BASE))["data"]
                identity={k:state[k] for k in ("epoch","generation")}
                assert_envelope(client.post(BASE+"/start",json={**identity,"geometry":"unknown"}),expected_status=422)
                state=assert_envelope(client.post(BASE+"/start",json={**identity,"density":"busy","mode":"adaptive"}))["data"]
                self.assertEqual(state["geometry"],"standard")
                identity={k:state[k] for k in ("epoch","generation")}
                step={**identity,"tick":0,"steps":5}
                state=assert_envelope(client.post(BASE+"/step",json=step))["data"]
                self.assertEqual(state["snapshot"]["tick"],5)
                self.assertFalse(state["snapshot"]["legacy_editor_compatible"])
                detached=service.scene()["snapshot"]
                detached["lanes"][0]["points"].clear()
                self.assertTrue(service.scene()["snapshot"]["lanes"][0]["points"])
                layout=state["snapshot"]["layout_id"]
                self.assertEqual(len(layout),64)
                for sid in VIEW_FLIPS:
                    v=assert_envelope(client.get(BASE+"/view",params={**identity,"tick":5,"source_id":sid}))["data"]
                    self.assertEqual(v["layout_id"],layout)
                    self.assertEqual(v["frame_number"],5)
                    shared=assert_envelope(client.get("/api/camera/simulation/observation",params={"engine":"native","source_id":sid}))["data"]
                    self.assertEqual(shared["observation"],v["observation"])
                    self.assertEqual(shared["agents"],v["agents"])
                    self.assertFalse(shared["legacy_editor_compatible"])
                    exact={**identity,"tick":5,"source_id":sid,"layout_id":layout,"engine":"native"}
                    binary=client.get("/api/camera/simulation/observation/frame",params=exact)
                    self.assertEqual(binary.status_code,200)
                    self.assertEqual(binary.headers["x-layout-id"],layout)
                    self.assertEqual(binary.content,client.get(BASE+"/frame",params={**identity,"tick":5,"source_id":sid}).content)
                    assert_envelope(client.get("/api/camera/simulation/observation/frame",params={**exact,"layout_id":"0"*64}),expected_status=409)
                    assert_envelope(client.get("/api/camera/simulation/observation/frame",params={**exact,"engine":"legacy"}),expected_status=409)
                    self.assertTrue(v["source_id"].startswith("native_eval_g"))
                    x,y=v["agents"][0]["x"],v["agents"][0]["y"]
                    a=state["snapshot"]["agents"][0]
                    self.assertAlmostEqual(x,1279-a["x"] if sid.endswith(("_c","_d")) else a["x"])
                    self.assertAlmostEqual(y,719-a["y"] if sid.endswith(("_b","_d")) else a["y"])
                    polygon=[[x-1,y-1],[x+1,y-1],[x+1,y+1],[x-1,y+1]]
                    region={**identity,"tick":5,"source_id":sid,"layout_id":layout,"coordinate_space":"native_projection_v1","polygon":polygon}
                    count=assert_envelope(client.post(BASE+"/region",json=region))["data"]
                    self.assertEqual(count["counts"],{"vehicle":1,"pedestrian":0})
                    self.assertFalse(count["persisted"])
                    self.assertFalse(v["observation"]["authoritative"])
                    self.assertFalse(v["observation"]["detector_observation"])
                    self.assertEqual(v["observation"],count["observation"])
                    self.assertEqual(len(count["polygon_world_m"]),4)
                    assert_envelope(client.post(BASE+"/region",json={**region,"coordinate_space":"legacy_pixels"}),expected_status=409)
                    assert_envelope(client.post(BASE+"/region",json={**region,"layout_id":"0"*64}),expected_status=409)
                    assert_envelope(client.post(BASE+"/region",json={**region,"polygon":[polygon[0],polygon[2],polygon[1],polygon[3]]}),expected_status=422)
                assert_envelope(client.post(BASE+"/step",json=step),expected_status=409)
                params={**identity,"tick":5}
                frozen=assert_envelope(client.post(BASE+"/pause",json={**params,"paused":True}))["data"]
                self.assertTrue(frozen["snapshot"]["paused"])
                assert_envelope(client.post(BASE+"/step",json={**params,"steps":1}),expected_status=409)
                self.assertEqual(assert_envelope(client.get(BASE))["data"]["snapshot"]["tick"],5)
                response=client.get(BASE+"/capture",params=params)
                self.assertEqual(response.status_code,200)
                with ZipFile(io.BytesIO(response.content)) as z:
                    observations=json.loads(z.read("observations.json"))
                    self.assertEqual(len(observations),4)
                    for sid in VIEW_FLIPS:
                        frame=client.get(BASE+"/frame",params={**params,"source_id":sid})
                        self.assertEqual(frame.status_code,200)
                        self.assertEqual(frame.content,z.read(sid+".png"))
                        meta=json.loads(z.read(sid+".json"))
                        self.assertEqual(meta["source_frame_number"],5)
                        self.assertEqual(meta["origin"],"synthetic_sumo_projection")
                        self.assertEqual(frame.headers["x-received-at-ms"],str(meta["source_received_at_ms"]))
                from app.services.inference import InferenceService
                from app.core.exceptions import AppError
                detector=InferenceService()
                native_frame=service.frame(**params,source_id="simulation_camera")
                with self.assertRaises(AppError) as rejection:
                    detector.detect_frame(native_frame)
                self.assertIn("not live detector inputs",str(rejection.exception))
                result=assert_envelope(client.get(BASE+"/export",params=params))["data"]
                self.assertEqual(len(result["timeline"]),5)
                self.assertEqual(result["trip_accounting"]["active"],["v0"])
                self.assertEqual(result["trip_accounting"]["offered"],["v0"])
                for kind, waits in result["waiting_episodes"].items():
                    self.assertEqual(waits["observed_agent_seconds"],result["summary"][kind+"_wait_agent_s"])
                self.assertFalse(result["production_experiment_parity"])
                self.assertFalse(sentinel.exists())
                self.assertFalse((root/"never-dataset").exists())
                assert_envelope(client.post(BASE+"/pause",json={**params,"paused":False}))
                def competing_step():
                    return client.post(BASE+"/step",json={**params,"steps":1}).status_code
                with ThreadPoolExecutor(max_workers=2) as pool:
                    self.assertEqual(sorted(pool.map(lambda _:competing_step(),range(2))),[200,409])
                self.assertEqual(service.scene()["snapshot"]["tick"],6)
                assert_envelope(client.get(BASE+"/frame",params={**params,"source_id":"simulation_camera"}),expected_status=409)
                stopped=assert_envelope(client.post(BASE+"/stop",json=identity))["data"]
                self.assertIsNone(stopped["snapshot"])
                self.assertTrue(sessions[0].closed)
                assert_envelope(client.post(BASE+"/start",json=identity),expected_status=409)
                # Both comparison arms copy one saved policy, never modify its bytes.
                policy=SignalRulesService(config_path=root/"policy.json",history_path=root/"policy-history.json",respect_environment=False)
                policy.save_config(policy.defaults())
                before=policy.config_path.read_bytes()
                current={k:stopped[k] for k in ("epoch","generation")}
                entered,release=Event(),Event()
                original_advance=FakeSession.advance
                def blocking_advance(session):
                    entered.set()
                    if not release.wait(5):
                        raise RuntimeError("Test comparison release timeout")
                    original_advance(session)
                with patch("app.services.native_evaluation.signal_rules_service",policy),patch.object(FakeSession,"advance",blocking_advance):
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        future=pool.submit(service.compare,**current,density="light",seed=42,duration_seconds=30)
                        try:
                            self.assertTrue(entered.wait(5))
                            self.assertEqual(service.scene()["status"],"busy")
                            assert_envelope(client.post(BASE+"/start",json=current),expected_status=409)
                            assert_envelope(client.post(BASE+"/stop",json=current),expected_status=409)
                        finally:
                            release.set()
                        archive=future.result(timeout=10)
                self.assertEqual(service.scene()["status"],"idle")
                with ZipFile(io.BytesIO(archive)) as z:
                    m=json.loads(z.read("manifest.json"))
                    self.assertFalse(m["production_experiment_parity"])
                    self.assertEqual(m["geometry"],"standard")
                    self.assertEqual(len(m["demand_digest"]),64)
                    self.assertIn("deltas.json",z.namelist())
                    self.assertEqual(m["profile"],policy.get_config()["active_profile"])
                    for mode in ("fixed","adaptive"):
                        result=json.loads(z.read(mode+".json"))
                        self.assertEqual(len(result["timeline"]),150)
                        self.assertEqual(result["layout_id"],layout)
                        self.assertEqual(result["policy_config"]["mode"],mode)
                self.assertEqual(policy.config_path.read_bytes(),before)
                self.assertTrue(all(s.closed for s in sessions))
                new=assert_envelope(client.post(BASE+"/start",json=current))["data"]
                with patch.object(sessions[-1],"set_phase",side_effect=lambda _:setattr(sessions[-1],"last_permission","GG")):
                    assert_envelope(client.post(BASE+"/step",json={"epoch":new["epoch"],"generation":new["generation"],"tick":0,"steps":1}),expected_status=503)
                self.assertTrue(sessions[-1].closed)
                self.assertIsNone(assert_envelope(client.get(BASE))["data"]["snapshot"])


if __name__=="__main__":
    unittest.main()
