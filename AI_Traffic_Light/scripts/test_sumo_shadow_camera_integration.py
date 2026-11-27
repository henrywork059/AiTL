"""Camera owner only forwards committed virtual phase observations."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/pc-studio/backend'))
from app.services.camera_frames import CameraFrameService

PHASE = {'phase': 'vehicle_green', 'vehicle_go': True, 'pedestrian_walk': False,
         'seconds_remaining': 12, 'base_cycle_seconds': 34, 'mode': 'fixed',
         'active_profile': 'fixture', 'active_rules': []}


class Tests(unittest.TestCase):
    def test_opt_in_preserves_authoritative_frames_and_pause(self):
        now = [0.0]
        shadow = Mock()
        shadow.status.return_value = {'status': 'unavailable', 'snapshot': None}
        service = CameraFrameService(simulation_seed=42, simulation_monotonic=lambda: now[0], shadow=shadow)
        reference = CameraFrameService(simulation_seed=42, simulation_monotonic=lambda: now[0])
        self.assertEqual(reference.shadow_diagnostics()['status'], 'disabled')
        with patch.object(service, '_simulation_signal_state_locked', return_value=PHASE), patch.object(reference, '_simulation_signal_state_locked', return_value=PHASE):
            service.set_simulation(True)
            reference.set_simulation(True)
            shadow.reset.assert_called_once_with(42)
            now[0] = 0.4
            a = service.simulation_scene_for('simulation_camera')
            b = reference.simulation_scene_for('simulation_camera')
            self.assertEqual(a['vehicles'], b['vehicles'])
            self.assertEqual(a['pedestrians'], b['pedestrians'])
            self.assertEqual(a['simulation_time_seconds'], b['simulation_time_seconds'])
            self.assertEqual(shadow.observe.call_count, 8)
            shadow.observe.assert_called_with('vehicle_green')
            service.configure_simulation(paused=True)
            now[0] = 1.0
            service.simulation_scene_for('simulation_camera')
            self.assertEqual(shadow.observe.call_count, 8)
            self.assertEqual(service.shadow_diagnostics()['status'], 'unavailable')
            service.set_simulation(False)
            shadow.stop.assert_called_once()
            self.assertIsNone(service.simulation_scene_for('simulation_camera'))
            reference.set_simulation(False)
        service.close_shadow()
        shadow.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
