"""Offline corridor demand and per-junction admission regressions."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.sumo_shadow_fixture import PhaseMap
from app.services.sumo_lane_scenarios import LaneVehicle
from app.services.sumo_corridor import corridor_permissions, validate_phases, write_corridor


class Tests(unittest.TestCase):
    def setUp(self):
        self.maps = {"A": PhaseMap((("WA_1", "AB_1", ""), (":A_w0_0", ":A_c0_0", "")),
                                  (0,), (1,), frozenset({":A_c0"})),
                     "B": PhaseMap((("AB_1", "BE_1", ""), (":B_w0_0", ":B_c0_0", "")),
                                  (0,), (1,), frozenset({":B_c0"}))}
        self.a = LaneVehicle("v0", "WA_1", 90, 5, 2.5, "AB")
        self.b = LaneVehicle("v1", "AB_1", 20, 5, 2.5, "BE")

    def states(self, a, b, rows=(), vehicles=(), people=()):
        return corridor_permissions(self.maps, {"A": a, "B": b}, rows, vehicles, people)

    def test_independent_phases_and_occupancy(self):
        self.assertEqual(self.states("vehicle_green", "pedestrian_green", (self.a, self.b)),
                         {"A": "Gr", "B": "rG"})
        self.assertEqual(self.states("vehicle_green", "vehicle_green", (self.a, self.b), people=(":A_c0",)),
                         {"A": "rr", "B": "Gr"})
        self.assertEqual(self.states("pedestrian_green", "pedestrian_green", vehicles=(":B_0",)),
                         {"A": "rG", "B": "rr"})
        for phase in ("vehicle_yellow", "pedestrian_flashing", "all_red"):
            self.assertEqual(self.states(phase, "vehicle_green", (self.a, self.b)), {"A": "rr", "B": "Gr"})

    def test_spillback_and_recovery(self):
        full = LaneVehicle("v1", "AB_1", 10, 5, 2.5, "BE")
        self.assertEqual(self.states("vehicle_green", "all_red", (self.a, full)), {"A": "rr", "B": "rr"})
        self.assertEqual(self.states("vehicle_green", "vehicle_green", (self.a, full)), {"A": "rr", "B": "Gr"})
        self.assertEqual(self.states("vehicle_green", "vehicle_green", (self.a, self.b)), {"A": "Gr", "B": "Gr"})

    def test_invalid_phase_and_seeded_route(self):
        for bad in ({}, {"A": "vehicle_green"}, {"A": "x", "B": "all_red"},
                    {"A": "all_red", "B": "all_red", "C": "all_red"}):
            with self.assertRaises(ValueError):
                validate_phases(bad)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_corridor(root, 42)
            data = (root / "routes.xml").read_bytes()
            write_corridor(root, 42)
            self.assertEqual(data, (root / "routes.xml").read_bytes())
            write_corridor(root, 43)
            self.assertNotEqual(data, (root / "routes.xml").read_bytes())
            xml = ET.fromstring(data)
            self.assertEqual(xml.find("route").get("edges"), "WA AB BE")
            self.assertEqual(len({v.get("id") for v in xml.findall("vehicle")}), 16)
            self.assertEqual(len(xml.findall("person")), 4)


if __name__ == "__main__":
    unittest.main()
