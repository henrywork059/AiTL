"""Actual deterministic fake-only demonstration and route regressions."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))

from app.services.fake_junction_demo import SCENARIOS, run_fake_junction_demo
from app.services.bench_output import FakeBenchAdapter
from app.routes.traffic import router
from app.core.middleware import RequestContextMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeJunctionDemoTests(unittest.TestCase):
    def test_all_scenarios_and_denials(self):
        for authorized in (False, True):
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario, authorized=authorized):
                    report = run_fake_junction_demo(scenario, authorized=authorized)
                    self.assertEqual(report, run_fake_junction_demo(scenario, authorized=authorized))
                    self.assertTrue(all(report["checks"].values()), report)
                    self.assertEqual(report["trace"][-1]["event"], "final_disconnected")
                    self.assertFalse(report["physical_output_allowed"])
                    self.assertFalse(report["audio_playback"])
                    self.assertEqual(report["time_basis"], "virtual_ms")
                    for row in report["trace"]:
                        for name in ("lighting", "speaker"):
                            self.assertFalse(row[name]["physical_output_allowed"])
                            if not authorized:
                                self.assertFalse(row[name]["active"])
                    if authorized and scenario == "nominal":
                        self.assertEqual(report["trace"][-2]["event"], "lease_expired")
                        self.assertEqual(report["trace"][-2]["time_ms"], 1000)
                    if authorized and scenario.endswith("_ack"):
                        self.assertEqual(report["trace"][-2]["event"], "fault_stop")
                        self.assertTrue(report["trace"][-3]["lighting"]["active"])
                        self.assertFalse(report["trace"][-2]["lighting"]["active"])

    def test_cleanup_on_unexpected_exception(self):
        instances = []
        original = FakeBenchAdapter.__init__
        def remember(adapter, *args, **kwargs):
            original(adapter, *args, **kwargs)
            instances.append(adapter)
        with patch.object(FakeBenchAdapter, "__init__", remember), patch(
                "app.services.fake_junction_demo.FakeSpeakerDemo.play", side_effect=RuntimeError("fixture")):
            with self.assertRaises(RuntimeError):
                run_fake_junction_demo("nominal", authorized=True)
        self.assertEqual(len(instances), 2)
        self.assertTrue(all(not a.connected and not a.active for a in instances))

    def test_api_validation_and_envelope(self):
        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)
        app.include_router(router, prefix="/api/traffic")
        client = TestClient(app)
        url = "/api/traffic/fake-junction-demo"
        for payload in ({"scenario": "traffic_signal"}, {"authorized": 1},
                        {"authorized": "true"}, {"adapter": "physical"}):
            self.assertEqual(client.post(url, json=payload).status_code, 422)
        response = client.post(url, json={"scenario": "missing_ack", "authorized": True},
                               headers={"X-Request-ID": "req_fake_demo"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["meta"]["request_id"], "req_fake_demo")
        self.assertTrue(all(body["data"]["checks"].values()))
        self.assertFalse(body["data"]["physical_output_allowed"])
        denied = client.post(url, json={}).json()["data"]
        self.assertFalse(denied["authorization_requested"])
        self.assertEqual(denied["trace"][-2]["event"], "authorization_denied")


if __name__ == "__main__":
    unittest.main()
