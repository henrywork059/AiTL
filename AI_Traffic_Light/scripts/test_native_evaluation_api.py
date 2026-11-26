"""Offline native evaluation API and isolated capture tests."""
from pathlib import Path
import io
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
                phase_loader=lambda _:PhaseMap((),(0,),(1,),frozenset()))
            self.addCleanup(service.close)
            sentinel=root/"never-write.json"
            with patch.dict(os.environ,{"AITL_SIGNAL_RULES":str(sentinel),"AITL_DATASET_DIR":str(root/"never-dataset")}), \
                 patch.object(routes,"native_evaluation_service",service), TestClient(build_test_app()) as client:
                state=assert_envelope(client.get(BASE))["data"]
                identity={k:state[k] for k in ("epoch","generation")}
                state=assert_envelope(client.post(BASE+"/start",json={**identity,"density":"busy","mode":"adaptive"}))["data"]
                identity={k:state[k] for k in ("epoch","generation")}
                step={**identity,"tick":0,"steps":5}
                state=assert_envelope(client.post(BASE+"/step",json=step))["data"]
                self.assertEqual(state["snapshot"]["tick"],5)
                assert_envelope(client.post(BASE+"/step",json=step),expected_status=409)
                params={**identity,"tick":5}
                frozen=assert_envelope(client.post(BASE+"/pause",json={**params,"paused":True}))["data"]
                self.assertTrue(frozen["snapshot"]["paused"])
                assert_envelope(client.post(BASE+"/step",json={**params,"steps":1}),expected_status=409)
                self.assertEqual(assert_envelope(client.get(BASE))["data"]["snapshot"]["tick"],5)
                response=client.get(BASE+"/capture",params=params)
                self.assertEqual(response.status_code,200)
                with ZipFile(io.BytesIO(response.content)) as z:
                    for sid in VIEW_FLIPS:
                        frame=client.get(BASE+"/frame",params={**params,"source_id":sid})
                        self.assertEqual(frame.status_code,200)
                        self.assertEqual(frame.content,z.read(sid+".png"))
                        meta=json.loads(z.read(sid+".json"))
                        self.assertEqual(meta["source_frame_number"],5)
                        self.assertEqual(meta["origin"],"synthetic_sumo_projection")
                        self.assertEqual(frame.headers["x-received-at-ms"],str(meta["source_received_at_ms"]))
                result=assert_envelope(client.get(BASE+"/export",params=params))["data"]
                self.assertEqual(len(result["timeline"]),5)
                self.assertFalse(result["production_experiment_parity"])
                self.assertFalse(sentinel.exists())
                self.assertFalse((root/"never-dataset").exists())
                assert_envelope(client.post(BASE+"/pause",json={**params,"paused":False}))
                assert_envelope(client.post(BASE+"/step",json={**params,"steps":1}))
                assert_envelope(client.get(BASE+"/frame",params={**params,"source_id":"simulation_camera"}),expected_status=409)
                stopped=assert_envelope(client.post(BASE+"/stop",json=identity))["data"]
                self.assertIsNone(stopped["snapshot"])
                self.assertTrue(sessions[0].closed)
                assert_envelope(client.post(BASE+"/start",json=identity),expected_status=409)


if __name__=="__main__":
    unittest.main()
