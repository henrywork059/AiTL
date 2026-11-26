"""API projection opt-in and immediate generation invalidation; no native installation."""
from pathlib import Path
import base64
from threading import Event, Thread
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from fastapi.testclient import TestClient
from test_camera_simulation_api import build_test_app, assert_envelope
from test_sumo_shadow_runtime import FakeSession, until
from app.services.camera_frames import CameraFrameService
from app.services.sumo_shadow_runtime import ShadowRuntime
from app.routes import camera as routes


class Tests(unittest.TestCase):
    def test_opt_in_and_invalidation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "network.xml"
            path.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            sessions = []
            def factory(seed):
                session = FakeSession(seed)
                session.network_path = path
                sessions.append(session)
                return session
            runtime = ShadowRuntime(factory, projection_enabled=True)
            self.addCleanup(runtime.close)
            service = CameraFrameService(shadow=runtime)
            with TestClient(build_test_app()) as client:
                with patch.object(routes, "camera_frame_service", CameraFrameService()):
                    data = assert_envelope(client.get("/api/camera/simulation/native-projection"))["data"]
                    self.assertEqual(data["status"], "disabled")
                    self.assertIsNone(data["snapshot"])
                    assert_envelope(client.get("/api/camera/simulation/native-frame", params={
                        "source_id": "simulation_camera", "generation": 1, "tick": 0}), expected_status=409)
                with patch.object(routes, "camera_frame_service", service):
                    runtime.reset(42)
                    until(lambda: runtime.status()["status"] == "running")
                    for _ in range(4):
                        runtime.observe("vehicle_green")
                    until(lambda: runtime.status()["snapshot"]["tick"] == 1)
                    data = assert_envelope(client.get("/api/camera/simulation/native-projection"))["data"]
                    self.assertEqual(data["snapshot"]["tick"], 1)
                    self.assertEqual(data["snapshot"]["agents"][0]["id"], "sumo:vehicle:0")
                    self.assertEqual(len(data["views_png_base64"]), 4)
                    light = assert_envelope(client.get("/api/camera/simulation/native-projection?format=scene"))["data"]
                    self.assertEqual(light["snapshot"]["agents"], data["snapshot"]["agents"])
                    self.assertEqual(light["snapshot"]["lanes"][0]["id"], "WC_1")
                    self.assertNotIn("views_png_base64", light)
                    self.assertEqual(runtime.status()["snapshot"]["tick"], 1)
                    params = {"source_id": "simulation_camera", "generation": data["generation"], "tick": 1}
                    with patch.object(runtime._projection, "render", wraps=runtime._projection.render) as render:
                        for sid, encoded in data["views_png_base64"].items():
                            response = client.get("/api/camera/simulation/native-frame", params={**params, "source_id": sid})
                            self.assertEqual(response.status_code, 200)
                            self.assertEqual(response.content, base64.b64decode(encoded))
                            self.assertEqual(response.headers["x-frame-number"], "1")
                            self.assertEqual(response.headers["x-native-generation"], str(data["generation"]))
                            self.assertEqual(response.headers["x-received-at-ms"], str(data["snapshot"]["received_at_ms"]))
                            self.assertEqual(response.headers["x-observation-origin"], "synthetic_sumo_projection")
                            self.assertTrue(response.headers["x-camera-source"].startswith("native_eval_g"))
                        self.assertEqual(render.call_count, 0, "Bundle and binary reads must reuse current publication")
                    assert_envelope(client.get("/api/camera/simulation/native-frame", params={**params,"tick":0}), expected_status=409)
                    assert_envelope(client.get("/api/camera/simulation/native-frame", params={**params,"source_id":"esp32"}), expected_status=422)
                    self.assertIsNone(service.latest_frame())
                    old_generation = data["generation"]
                    runtime.stop()
                    data = assert_envelope(client.get("/api/camera/simulation/native-projection"))["data"]
                    self.assertIsNone(data["snapshot"])
                    self.assertGreater(data["generation"], old_generation)
                    assert_envelope(client.get("/api/camera/simulation/native-frame", params=params), expected_status=409)
                    runtime.reset(43)
                    until(lambda: runtime.status()["status"] == "running")
                    sessions[-1].fail = True
                    for _ in range(4):
                        runtime.observe("all_red")
                    until(lambda: runtime.status()["status"] == "unavailable")
                    data = assert_envelope(client.get("/api/camera/simulation/native-projection"))["data"]
                    self.assertIsNone(data["snapshot"])
                    self.assertNotIn("views_png_base64", data)
            runtime.close()
            self.assertTrue(all(s.closed for s in sessions))


    def test_retirement_during_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "network.xml"
            path.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            def factory(seed):
                session = FakeSession(seed)
                session.network_path = path
                return session
            runtime = ShadowRuntime(factory, projection_enabled=True)
            self.addCleanup(runtime.close)
            runtime.reset(42)
            until(lambda: runtime.status()["status"] == "running")
            generation = runtime.status()["generation"]
            entered, release = Event(), Event()
            results = []
            original = runtime._projection.render
            def blocked(snap):
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test timed out")
                return original(snap)
            with patch.object(runtime._projection, "render", side_effect=blocked):
                thread = Thread(target=lambda: results.append(runtime.projection_frame(
                    "simulation_camera", generation=generation, tick=0)))
                thread.start()
                try:
                    self.assertTrue(entered.wait(5))
                    self.assertIsNone(runtime.projection_frame("simulation_camera", generation=generation, tick=0))
                    runtime.stop()
                finally:
                    release.set()
                    thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(results, [None])
                self.assertIsNone(runtime._frame_cache)
            runtime.reset(43)
            until(lambda: runtime.status()["status"] == "running")
            self.assertIsNone(runtime.projection_frame("simulation_camera", generation=generation, tick=0))
            new_generation = runtime.status()["generation"]
            self.assertIsNotNone(runtime.projection_frame("simulation_camera", generation=new_generation, tick=0))


if __name__ == "__main__":
    unittest.main()
