"""API projection opt-in and immediate generation invalidation; no native installation."""
from pathlib import Path
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
                    self.assertIsNone(service.latest_frame())
                    old_generation = data["generation"]
                    runtime.stop()
                    data = assert_envelope(client.get("/api/camera/simulation/native-projection"))["data"]
                    self.assertIsNone(data["snapshot"])
                    self.assertGreater(data["generation"], old_generation)
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


if __name__ == "__main__":
    unittest.main()
