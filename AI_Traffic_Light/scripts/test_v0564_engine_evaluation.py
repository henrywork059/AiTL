"""Offline checks of evaluation fixture, trace normalization and blocker reporting."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from evaluate_simulation_engine import evaluate, trace_summary, write_scenario


class EngineEvaluationTests(unittest.TestCase):
    def test_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_scenario(root)
            nodes = ET.parse(root / 'nodes.xml').getroot()
            edges = ET.parse(root / 'edges.xml').getroot()
            routes = ET.parse(root / 'routes.xml').getroot()
            self.assertEqual(len(nodes), 5)
            self.assertEqual(len(edges), 8)
            self.assertEqual(nodes.find("node[@id='C']").get('type'), 'traffic_light')
            self.assertTrue(all(e.get('sidewalkWidth') == '2' for e in edges))
            self.assertEqual(len(routes.findall('vehicle')), 12)
            self.assertEqual(len(routes.findall('person')), 12)
            departures = [float(e.get('depart')) for e in routes if e.tag in ('vehicle', 'person')]
            self.assertEqual(departures, sorted(departures))

    def test_canonical_trace(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'trace.xml'
            a = '<vehicle id="a" x="1" y="2" speed="3"/>'
            b = '<vehicle id="b" x="4" y="5" speed="6"/>'
            def summary(rows, header=''):
                p.write_text(f'<fcd-export>{header}<timestep time="0.0">{rows}</timestep></fcd-export>')
                return trace_summary(p, 'vehicle')
            self.assertEqual(summary(a+b), summary(b+a, '<!--different header-->'))
            self.assertNotEqual(summary(a+b)['sha256'], summary(a.replace('x="1"', 'x="2"')+b)['sha256'])
            self.assertEqual(summary(a+b)['observed_agents'], 2)
            with self.assertRaises(ValueError):
                summary('')
            p.write_text(f'<fcd-export><timestep time="1">{a}</timestep><timestep time="1">{b}</timestep></fcd-export>')
            with self.assertRaises(ValueError):
                trace_summary(p, 'vehicle')

    def test_missing_engine_is_not_a_pass(self):
        with patch('evaluate_simulation_engine.shutil.which', return_value=None):
            result = evaluate()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['runs'], [])
        self.assertIn('sumo', result['reason'])


if __name__ == '__main__':
    unittest.main()
