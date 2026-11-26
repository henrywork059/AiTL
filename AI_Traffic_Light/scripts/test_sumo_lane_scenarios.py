"""Offline admission and deterministic demand regressions, no native packages."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.sumo_shadow_fixture import PhaseMap
from app.services.sumo_lane_scenarios import LaneVehicle, choose_permission, write_lane_demand


class Tests(unittest.TestCase):
    def setUp(self):
        self.mapping = PhaseMap((("WC_1", "CE_1", ""), ("WC_1", "CN_1", ""),
                                 ("WC_1", "CS_1", ""), ("EC_1", "CW_1", ""),
                                 (":C_w0_0", ":C_c0_0", "")), (0, 3), (4,), frozenset({":C_c0"}))
        self.lead = LaneVehicle("lead", "WC_1", 90, 5, 2.5, "CE")
        self.follow = LaneVehicle("follow", "WC_1", 80, 5, 2.5, "CN")
        self.other = LaneVehicle("other", "EC_1", 85, 5, 2.5, "CW")

    def state(self, *vehicles, phase="vehicle_green", inside=False, ped=False):
        return choose_permission(self.mapping, phase, vehicles, vehicle_inside=inside, pedestrian_inside=ped)

    def test_fifo_turn_and_blocked_exit(self):
        self.assertEqual(self.state(self.follow, self.lead), "Grrrr")
        blocker = LaneVehicle("blocker", "CE_1", 10, 5, 2.5)
        self.assertEqual(self.state(self.follow, self.lead, blocker), "rrrrr")
        self.assertEqual(self.state(self.follow, self.lead, blocker, self.other), "rrrGr")
        self.assertEqual(self.state(self.follow), "rGrrr")
        self.assertEqual(self.state(LaneVehicle("right", "WC_1", 80, 5, 2.5, "CS")), "rrGrr")
        clear = LaneVehicle("blocker", "CE_1", 12.5, 5, 2.5)
        self.assertEqual(self.state(self.lead, clear), "Grrrr")

    def test_protected_phase_and_exclusion(self):
        self.assertEqual(self.state(self.lead, self.other, inside=True), "rrrrr")
        self.assertEqual(self.state(self.lead, ped=True), "rrrrr")
        self.assertEqual(self.state(self.lead, phase="pedestrian_green", inside=True), "rrrrr")
        self.assertEqual(self.state(self.lead, phase="pedestrian_green"), "rrrrG")
        for phase in ("vehicle_yellow", "pedestrian_flashing", "all_red", "unknown"):
            self.assertEqual(self.state(self.lead, phase=phase), "rrrrr")

    def test_seeded_demand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_lane_demand(root, 42)
            first = (root / "routes.xml").read_bytes()
            write_lane_demand(root, 42)
            self.assertEqual(first, (root / "routes.xml").read_bytes())
            write_lane_demand(root, 43)
            self.assertNotEqual(first, (root / "routes.xml").read_bytes())
            routes = ET.fromstring(first)
            self.assertEqual(len(routes.findall("vehicle")), 17)
            self.assertEqual(len(routes.findall("person")), 4)
            self.assertEqual(routes.find("vehicle/stop").get("lane"), "CE_1")


if __name__ == "__main__":
    unittest.main()
