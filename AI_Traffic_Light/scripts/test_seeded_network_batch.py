"""Focused actual isolated queue-model smoke and paired-delta invariants."""
import csv
import io
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from seeded_network_batch import execute, MODES, METRICS, FAIRNESS_MODES
from verify_seeded_network_evidence import verify, verify_members

class SeededBatchTest(unittest.TestCase):
    def test_real_paired_smoke(self):
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / "evidence"
            manifest = execute(out, seeds=(42,), densities=("busy",), duration=30)
            self.assertTrue(manifest["repeat_primary_metrics_and_demand_equal"])
            self.assertTrue(manifest["repeat_intersection_fairness_equal"])
            self.assertFalse(manifest["physical_output_allowed"])
            audit = verify(out)
            self.assertEqual(audit["matched_cases"], 1)
            self.assertEqual(audit["primary_rows"], 3)
            self.assertEqual(audit["fairness_rows"], 8)
            self.assertEqual(audit["busy_repeats"], 1)
            self.assertGreater(audit["timeline_samples"], 0)
            self.assertGreaterEqual(audit["decision_records"], 0)
            self.assertEqual(audit["conservation_runs"], 4)
            # Rehash a deliberately changed CSV: consistency must still fail.
            members = {p.name: p.read_bytes() for p in out.iterdir()}
            rows = list(csv.reader(members["paired-metrics.csv"].decode("utf-8").splitlines()))
            rows[1][4] = str(float(rows[1][4]) + 1)
            import io
            buffer = io.StringIO()
            csv.writer(buffer).writerows(rows)
            members["paired-metrics.csv"] = buffer.getvalue().encode("utf-8")
            with self.assertRaisesRegex(ValueError, "Member digest mismatch"):
                verify_members(list(members), members.__getitem__)
            altered_manifest = json.loads(members["manifest.json"])
            altered_manifest["sha256"]["paired-metrics.csv"] = hashlib.sha256(members["paired-metrics.csv"]).hexdigest()
            members["manifest.json"] = json.dumps(altered_manifest).encode("utf-8")
            with self.assertRaisesRegex(ValueError, "CSV metric differs"):
                verify_members(list(members), members.__getitem__)
            self.assertEqual(manifest["busy_repeats"], [{"seed": 42, "file": "busy-42-repeat.json", "primary_fairness_and_demand_equal": True}])
            self.assertEqual(sum(manifest["cooperative_vs_adaptive_pedestrian_wait_signs"]["busy"].values()), 1)
            row = manifest["records"][0]
            raw = json.loads((out / "busy-42.json").read_text(encoding="utf-8"))
            self.assertEqual(row["demand_sha256"], raw["scenario"]["arrival_plan"]["fingerprint_sha256"])
            with (out / "paired-metrics.csv").open(encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual([r["mode"] for r in rows], list(MODES))
            for item in rows:
                for key in METRICS:
                    self.assertEqual(float(item[key]), raw[item["mode"]]["network_metrics"][key])
            with (out / "intersection-fairness.csv").open(encoding="utf-8") as source:
                fairness = list(csv.DictReader(source))
            self.assertEqual(len(fairness), len(FAIRNESS_MODES) * 2)
            self.assertEqual({r["mode"] for r in fairness}, set(FAIRNESS_MODES))
            for item in fairness:
                local = raw[item["mode"]]["intersections"][item["intersection_id"]]["metrics"]
                self.assertEqual(float(item["pedestrian_wait_person_seconds"]), local["waiting"]["pedestrian"]["total_seconds"])
                self.assertEqual(int(item["pedestrians_served"]), local["throughput"]["pedestrians_served"])
                self.assertEqual(item["demand_sha256"], row["demand_sha256"])
            for key in METRICS:
                self.assertAlmostEqual(row["pedestrian_aware_minus_cooperative"][key], raw["pedestrian_aware_cooperative"]["network_metrics"][key] - raw["cooperative"]["network_metrics"][key])
            for name, digest in manifest["sha256"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)
            for key in METRICS:
                self.assertAlmostEqual(row["paired_deltas"]["cooperative_minus_fixed"][key],
                    row["metrics"]["cooperative"][key] - row["metrics"]["fixed"][key])


            # A changed trace/decision CSV cannot be laundered by recomputing
            # its manifest member digest; compare exported rows to raw run JSON.
            original = {p.name: p.read_bytes() for p in out.iterdir()}
            for filename, field in (("busy-42-timeline.csv", "fixed_source_vehicle_queue"),
                                    ("busy-42-decisions.csv", "action")):
                members = dict(original)
                rows = list(csv.DictReader(io.StringIO(members[filename].decode("utf-8"))))
                self.assertTrue(rows)
                rows[0][field] = "999" if field.endswith("queue") else "corrupted"
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                members[filename] = buf.getvalue().encode("utf-8")
                forged = json.loads(members["manifest.json"])
                forged["sha256"][filename] = hashlib.sha256(members[filename]).hexdigest()
                members["manifest.json"] = json.dumps(forged).encode("utf-8")
                with self.assertRaisesRegex(ValueError, "Timeline|Decision"):
                    verify_members(list(members), members.__getitem__)

            # Change a raw-only arrival count and rehash; the cross-field
            # conservation audit must catch what CSV equality alone cannot.
            members = dict(original)
            changed = json.loads(members["busy-42.json"])
            node = changed["fixed"]["timeline"][-1]["source"]["intersection_id"]
            changed["fixed"]["intersections"][node]["metrics"]["throughput"]["external_vehicle_arrivals"] += 1
            members["busy-42.json"] = json.dumps(changed).encode("utf-8")
            forged = json.loads(members["manifest.json"])
            forged["sha256"]["busy-42.json"] = hashlib.sha256(members["busy-42.json"]).hexdigest()
            members["manifest.json"] = json.dumps(forged).encode("utf-8")
            with self.assertRaisesRegex(ValueError, "Conservation vehicle balance"):
                verify_members(list(members), members.__getitem__)

if __name__ == "__main__":
    unittest.main()
