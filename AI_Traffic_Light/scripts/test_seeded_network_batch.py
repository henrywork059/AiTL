"""Focused actual isolated queue-model smoke and paired-delta invariants."""
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from seeded_network_batch import execute, MODES, METRICS

class SeededBatchTest(unittest.TestCase):
    def test_real_paired_smoke(self):
        with TemporaryDirectory() as temporary:
            out = Path(temporary) / "evidence"
            manifest = execute(out, seeds=(42,), densities=("normal",), duration=30)
            self.assertTrue(manifest["repeat_primary_metrics_and_demand_equal"])
            self.assertFalse(manifest["physical_output_allowed"])
            row = manifest["records"][0]
            raw = json.loads((out / "normal-42.json").read_text(encoding="utf-8"))
            self.assertEqual(row["demand_sha256"], raw["scenario"]["arrival_plan"]["fingerprint_sha256"])
            with (out / "paired-metrics.csv").open(encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual([r["mode"] for r in rows], list(MODES))
            for item in rows:
                for key in METRICS:
                    self.assertEqual(float(item[key]), raw[item["mode"]]["network_metrics"][key])
            for name, digest in manifest["sha256"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)
            for key in METRICS:
                self.assertAlmostEqual(row["paired_deltas"]["cooperative_minus_fixed"][key],
                    row["metrics"]["cooperative"][key] - row["metrics"]["fixed"][key])

if __name__ == "__main__":
    unittest.main()
