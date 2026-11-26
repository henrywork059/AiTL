"""Pure projection and injected lifecycle regression, no native dependency."""
from pathlib import Path
import csv
import io
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.sumo_projection import Projection, VIEW_FLIPS, export_csv
from app.services.sumo_projection_session import NativeProjectionSession
from app.services.sumo_shadow_adapter import ShadowAgent


class Fake:
    def __init__(self, path):
        self.network_path = path
        self.tick = 0
        self.closed = False
        self.fail = False

    def set_phase(self, phase):
        self.phase = phase

    def advance(self):
        if self.fail:
            raise RuntimeError("fixture failure")
        self.tick += 1

    def agents(self):
        return (ShadowAgent("vehicle", "v0", self.tick, 1, 2, "WA"),)

    def close(self):
        self.closed = True


class Tests(unittest.TestCase):
    def test_projection_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "network.xml"
            path.write_text('<net><edge id="WA"><lane id="WA_0" shape="0,0 20,0" width="3.2"/></edge>'
                            '<edge id="X" function="crossing"><lane id="X_0" shape="10,-5 10,5" width="2"/></edge></net>')
            layout = Projection.load(path)
            for sid in VIEW_FLIPS:
                x, y = layout.world(*layout.pixel(4, 1, sid), sid)
                self.assertAlmostEqual(x, 4)
                self.assertAlmostEqual(y, 1)
            with self.assertRaises(ValueError):
                layout.pixel(10000, 0)
            sessions = []
            def factory(seed):
                sessions.append(Fake(path))
                return sessions[-1]
            runner = NativeProjectionSession(factory)
            try:
                reset, _ = runner.reset(42)
                meta, views = runner.step("vehicle_green")
                self.assertEqual(meta["tick"], 1)
                self.assertEqual(meta["agents"][0]["id"], "sumo:vehicle:v0")
                image = lambda sid: cv2.imdecode(np.frombuffer(views[sid], np.uint8), cv2.IMREAD_COLOR)
                for sid, flip in VIEW_FLIPS.items():
                    if flip is not None:
                        self.assertTrue(np.array_equal(image(sid), cv2.flip(image("simulation_camera"), flip)))
                row = next(csv.DictReader(io.StringIO(export_csv(meta))))
                self.assertEqual(row["id"], meta["agents"][0]["id"])
                self.assertEqual(float(row["x"]), meta["agents"][0]["x"])
                runner.pause(True)
                self.assertEqual(runner.step("all_red")[0]["tick"], 1)
                runner.pause(False)
                self.assertEqual(runner.step("all_red")[0]["tick"], 2)
                new, _ = runner.reset(42)
                self.assertTrue(sessions[0].closed)
                self.assertEqual(new["generation"], reset["generation"] + 1)
                self.assertEqual(new["tick"], 0)
                sessions[-1].fail = True
                with self.assertRaises(RuntimeError):
                    runner.step("all_red")
                self.assertIsNone(runner.read())
                self.assertTrue(sessions[-1].closed)
            finally:
                runner.close()


if __name__ == "__main__":
    unittest.main()
